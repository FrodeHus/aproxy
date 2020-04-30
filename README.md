# aproxy
Simple utility that lets you define multiple proxies in a config file.

To install: `pip3 install aproxy`

# Usage

## Single proxy

`aproxy proxy single --local-port 1234 --remote-host 127.0.0.1 --remote-port 8080`

## Multiple proxies

Example config `proxy.json`:

```json
{
    "proxies": [
        {
            "name": "target web server",
            "localPort": 4444,
            "remotePort": 80,
            "remoteHost": "254.312.1.0",
            "verbosity": 0
        },
        {
            "name": "target database",
            "localPort": 3306,
            "localHost": "127.0.0.1",
            "remotePort": 3306,
            "remoteHost": "1001.312.4.1",
            "verbosity": 3
        }
    ]
}
```

Start all the proxies with `aproxy proxy start --configFile proxy.json`

```text
Loaded config for 2 proxies
[*] Listening on 0.0.0.0:4444
[*] Listening on 127.0.0.1:3306

[==>] Received incoming connection from 127.0.0.1:52172
[victim web server ==>] Received 80 bytes of data from LOCAL
00000000: 47 45 54 20 2F 20 48 54  54 50 2F 31 2E 31 0D 0A  GET / HTTP/1.1..
00000010: 48 6F 73 74 3A 20 77 77  77 2E 66 72 6F 64 65 68  Host: www.frodeh
00000020: 75 73 2E 64 65 76 0D 0A  55 73 65 72 2D 41 67 65  us.dev..User-Age
00000030: 6E 74 3A 20 63 75 72 6C  2F 37 2E 35 38 2E 30 0D  nt: curl/7.58.0.
00000040: 0A 41 63 63 65 70 74 3A  20 2A 2F 2A 0D 0A 0D 0A  .Accept: */*....

```

# Providers

You can use providers if you need to pivot through other protocols to reach your destination.
For example, you can proxy to a remote host on the other side of a SSH server by using the SSH provider.

Define the provider configuration block in you `proxy.json` and then reference the provider configuration you wish to use in the proxy configuration:

```json
{
    "providerConfig": [
        {
            "name": "provider1",
            "provider": {
                "name": "dummyprovider",
                "username": "abcdef",
                "password": "dummy"
            }
        }
    ],
    "proxies": [
        {
            "localPort": 4444,
            "localHost": "0.0.0.0",
            "remotePort": 443,
            "remoteHost": "192.168.0.1",
            "verbosity": 0,
            "provider": "provider1"
        }
   ]
}
```

You define multiple configurations for the same type of provider by giving them different names and then reference those in the various proxy configurations.

## SSH local port forwarding

SSH provider configuration:

```json
{
    "name": "myprivateserver",
    "provider": {
        "name": "ssh",
        "host": "172.16.0.1",
        "user": "dummy",
    }
}
```

This can now be used by different proxies reaching different remote hosts:

```json
"proxies": [
        {
            "name": "securewebserver",
            "localPort": 4444,
            "localHost": "0.0.0.0",
            "remotePort": 443,
            "remoteHost": "192.168.0.2",
            "verbosity": 0,
            "provider": "myprivateserver"
        },
        {
            "name": "insecurewebserver",
            "localPort": 5555,
            "localHost": "0.0.0.0",
            "remotePort": 80,
            "remoteHost": "192.168.0.5",
            "verbosity": 3,
            "provider": "myprivateserver"
        }
    ]
```

## Kubernetes

Sometimes you might need access to resources that are only available to a kubernetes cluster, i.e databases that are locked down on a virtual network only open to the cluster.

This is when you can use the kubernetes provider to open a proxy through a running pod on the cluster and tunnel traffic through that.

__experimental feature - still under development__

Kubernetes provider configuration:

```json
{
    "name": "k8s",
    "provider": {
        "name": "kubernetes",
        "context": "dummy-cluster"
    }
}

```
This will connect to the specified context using the user's kubeconfig. Later, other ways will be available.

Once this provider is configured, it can be used the same way as other providers.

Sample proxy config using kubernetes provider:

```json
{
    "name": "sql",
    "localPort": 1433,
    "remotePort": 1433,
    "remoteHost": "10.0.1.10",
    "provider": "k8s"
}
```

Once the provider connects, it will look for eligble pods that can serve as a staging area for the proxy. 
You will also be able to specify a specific pod that you have prepared in advance.

It does this by checking for certain permissions and available software installed on the pod. If able to install software, it will do so.

This is, again, work in progress. 

Sample output:

```text
[*] active host is https://demo-b3c208b3.01841885-cab3-44b7-a9a2-90d60695807f.privatelink.westeurope.azmk8s.io:8443
[*] found 25 pods - checking for eligible staging candidates (this may take a while)
[*] Processing... ◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉ 100%
[+] valid pods for proxy staging: 2
    kube-system/kube-proxy-597hr
    kube-system/kube-proxy-vxpdw
[+] selecting kube-system/kube-proxy-597hr [exec: FULL] [user: root]    [pkg_mgr: APT]  [utils: ['socat', 'python']]
[+] starting reverse proxy on kube-system/kube-proxy-597hr using socat for 10.0.1.10:1433
```

## Provider dependencies

It is possible to tunnel through providers.

### Tunnel example

You need to access a MySQL server that is only accessible to the kubernetes cluster. 

You can only connect to kubernetes API server through a jump server that supports SSH. 

Basic setup would be something like this:

```text
you -> ssh -> kubernetes -> mysql
```

The kubernetes provider is then dependent on the SSH provider and will be a client of that provider.

#### Sample config

```json
{
    "providerConfig": [
        {
            "name": "k8s",
            "dependsOn": [
                "jumpserver"
            ],
            "provider": {
                "name": "kubernetes",
                "stagingPod": "dummy",
                "context": "dummy"
            }
        },
        {
            "name": "jumpserver",
            "provider": {
                "name": "ssh",
                "host": "127.0.0.1",
                "user": "abcdef",
            }
        }
    ],
    "proxies": [
        {
            "localPort": 443,
            "localHost": "0.0.0.0",
            "remotePort": 443,
            "remoteHost": "<ip of kubernetes API server>",
            "verbosity": 0,
            "provider": "jumpserver"
        },
        {
            "localPort": 3306,
            "remotePort": 3306,
            "remoteHost": "<ip of mysql server on other side of kubernetes>",
            "provider": "k8s"
        }
    ]
}
```

## Future notes

- Plugin support for manipulating data going in/out.
- kubernetes provider
