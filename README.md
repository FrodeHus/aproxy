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

## Future notes

- Plugin support for manipulating data going in/out.
- Encrypted channels
- Port-forwarding through SSH
