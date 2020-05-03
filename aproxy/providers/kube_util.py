from progress.bar import FillingCirclesBar
from aproxy.providers.provider_config import ProviderConfig
from aproxy.providers.staging_pod import PackageManager, StagingPod
from tempfile import TemporaryFile
from kubernetes.stream.stream import stream
from kubernetes.client import CoreV1Api, V1Pod
import tarfile
import traceback
import sys


def find_eligible_staging_pod(client: CoreV1Api, exclude_namespaces: [] = None):
    pods = client.list_pod_for_all_namespaces()
    available_pods = pods.items
    if exclude_namespaces:
        available_pods = [
            pod
            for pod in available_pods
            if pod.metadata.namespace not in exclude_namespaces
        ]

    print(
        f"[*] found {len(available_pods)} pods - checking for eligible staging candidates (this may take a while)"
    )
    pod_capabilities = []
    with FillingCirclesBar("[*] Processing...", max=len(available_pods)) as bar:
        for pod_info in available_pods:
            capabilities = run_checks(client, pod_info)
            pod_capabilities.append(capabilities)
            bar.next()

    eligible_pods = [pod for pod in pod_capabilities if pod.can_be_staging()]
    print(f"[+] valid pods for proxy staging: {len(eligible_pods)}")
    for pod in eligible_pods:
        print(f"\t{pod.namespace}/{pod.pod_name}")

    staging_pods = [pod for pod in eligible_pods if pod.has_dependencies_installed()]
    if len(staging_pods) == 0:
        install_dependencies(client, eligible_pods)

    print(f"[+] selecting {staging_pods[0]}")
    return staging_pods[0]


def install_dependencies(k8sclient: CoreV1Api, staging_pods: []):
    for staging_pod in [pod for pod in staging_pods if pod.can_be_staging()]:
        print(
            f"[*] installing socat in {staging_pod.namespace}/{staging_pod.pod_name} using {staging_pod.package_manager.name}"
        )

        if staging_pod.can_exec and staging_pod.package_manager == PackageManager.APT:
            result = pod_exec(
                "apt update && apt install -y socat",
                staging_pod.pod_name,
                staging_pod.namespace,
            )


def run_checks(client: CoreV1Api, pod_info: V1Pod) -> StagingPod:
    user_script = "whoami"
    user = pod_exec(user_script, pod_info.metadata.name, pod_info.metadata.namespace)

    utils = find_required_utils(client, pod_info)
    pkg_manager = find_package_manager(client, pod_info)

    return StagingPod(
        user, pkg_manager, utils, pod_info.metadata.name, pod_info.metadata.namespace,
    )


def find_package_manager(client: CoreV1Api, pod_info: V1Pod):
    pkg_manager_script = """#!/bin/sh
if [ -x "$(which apk 2>/dev/null)" ]
then
    echo apk
fi
if [ -x "$(which apt-get 2>/dev/null)" ]
then
    echo apt
fi
if [ -x "$(which zypper 2>/dev/null)" ]
then
    echo zypper
fi
if [ -x "$(which yum 2>/dev/null)" ]
then
    echo yum
fi
"""

    upload_script(
        client,
        pkg_manager_script,
        "pkg_manager.sh",
        pod_info.metadata.name,
        pod_info.metadata.namespace,
    )
    pkg_manager = pod_exec(
        "/bin/sh /tmp/pkg_manager.sh",
        pod_info.metadata.name,
        pod_info.metadata.namespace,
    )

    if pkg_manager and pkg_manager.find("exec failed") != -1:
        pkg_manager = "none"

    return pkg_manager


def find_required_utils(client: CoreV1Api, pod_info: V1Pod):
    script = """#!/bin/sh
if [ -x "$(which socat 2>/dev/null)" ]
then
    echo socat
fi
if [ -x "$(which python 2>/dev/null)" ]
then
    echo python
fi
"""
    upload_script(
        client,
        script,
        "util_check.sh",
        pod_info.metadata.name,
        pod_info.metadata.namespace,
    )
    utils = pod_exec(
        "sh /tmp/util_check.sh", pod_info.metadata.name, pod_info.metadata.namespace,
    )

    if utils and utils.find("exec failed") != -1:
        utils = None
    elif utils:
        utils = utils.split("\n")

    return utils


def find_services(client: CoreV1Api):
    services = []
    service_list = client.list_service_for_all_namespaces()
    for svc in service_list.items:
        services.append((svc.metadata.name, svc.spec.cluster_ip))
    return services


def pod_exec(cmd: str, name: str, namespace: str = "default", tty=False):
    client = CoreV1Api()
    exec_command = cmd.split(" ")
    try:
        resp = stream(
            client.connect_get_namespaced_pod_exec,
            name,
            namespace,
            command=exec_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=tty,
            _request_timeout=5.0,
        )
        if not resp:
            return None
        if resp.lower().find("no such file or directory") != -1:
            return None

        return resp.strip()
    except RuntimeError as err:
        print(f"[!!] failed when executing command '{cmd}''")
        print(traceback.format_exc())
        return None


def setup_staging(
    client: CoreV1Api, staging_pod: StagingPod, remote_address: str, remote_port: int,
):
    if not staging_pod:
        print("[!!] no staging pod available")
        return False
    print(
        f"[+] starting proxy on {staging_pod.namespace}/{staging_pod.pod_name} using {staging_pod.utils[0]} for {remote_address}:{remote_port}"
    )

    script = f"""#!/bin/sh
if [ -z "$(ps -ef | grep '[s]ocat tcp-l:{remote_port}')" ]
then 
socat tcp-l:{remote_port},reuseaddr,fork tcp:{remote_address}:{remote_port} &
fi
"""
    script_name = f"socat-{str(remote_port)}.sh"
    upload_script(
        client, script, script_name, staging_pod.pod_name, staging_pod.namespace
    )

    result = pod_exec(
        f"sh /tmp/{script_name}", staging_pod.pod_name, staging_pod.namespace,
    )
    return True


def upload_script(
    client: CoreV1Api, script: str, file_name: str, pod_name: str, namespace: str
):
    script += f"\nrm -Rf /tmp/{file_name}\n"
    with TemporaryFile() as file:
        file.write(script.encode())
        size = file.tell()
        file.seek(0)

        upload_to_pod(client, pod_name, namespace, file_name, file, size)


def upload_to_pod(
    client: CoreV1Api,
    pod_name: str,
    namespace: str,
    file_name,
    file,
    file_size,
    verbose=False,
):
    if verbose:
        print(f"[*] uploading payload [{file_name}]")

    cmd = ["tar", "xvf", "-", "-C", "/tmp"]
    try:
        resp = stream(
            client.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            command=cmd,
            stderr=True,
            stdin=True,
            stdout=True,
            _preload_content=False,
        )

        source_file = file

        with TemporaryFile() as tar_buffer:
            with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
                tarinfo = tarfile.TarInfo(file_name)
                tarinfo.size = file_size
                tar.addfile(tarinfo, fileobj=file)

            tar_buffer.seek(0)
            commands = []
            commands.append(tar_buffer.read())

            while resp.is_open():
                resp.update(timeout=1)
                if commands:
                    c = commands.pop(0)
                    resp.write_stdin(c)
                else:
                    break
            resp.close()
    except:
        print("[!!] failed to upload file")
        return None
