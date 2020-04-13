# aproxy
Simple utility that lets you define multiple proxies in a config file.

To install: `pip3 install aproxy`

# Usage

## Single proxy

`aproxy proxy single --local-port 1234 --remote-host 127.0.0.1 --remote-port 8080`

## Multiple proxies

Example config `proxy.json`:

```
{
    "proxies": [
        {
            "name": "victim web server",
            "localPort": 4444,
            "remotePort": 80,
            "remoteHost": "254.312.1.0",
            "verbosity": 0
        },
        {
            "name": "victim database",
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

```
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
            "name": "securwebserver",
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

## Future notes

- Plugin support for manipulating data going in/out.
