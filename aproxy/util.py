
# taken from http://code.activatestate.com/recipes/142812-hex-dumper/
def hexdump(src, length=16):
    result = []
    digits = 4 if isinstance(src, str) else 2
    for i in range(0, len(src), length):
        s = src[i : i + length]
        hexa = b" ".join(["%0*X" % (digits, ord(chr(x))) for x in s])
        text = b"".join([x if 0x20 <= ord(chr(x)) < 0x7F else b"." for x in s])
        result.append(b"%04X    %-*s    %s" % (i, length * (digits + 1), hexa, text))
    print(b"\n".join(result))

