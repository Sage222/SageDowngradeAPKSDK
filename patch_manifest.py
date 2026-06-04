"""
Binary AndroidManifest.xml patcher.
Searches for the integer value 33 (SDK version) stored as a typed int
in the binary XML, patches it to the target value.
"""
import zipfile, struct, sys, os

apk_in  = sys.argv[1]
apk_out = sys.argv[2]
new_min = int(sys.argv[3])

with zipfile.ZipFile(apk_in, "r") as z:
    manifest = bytearray(z.read("AndroidManifest.xml"))

# In binary Android XML a typed integer is encoded as:
#   08 00       - size = 8
#   00          - res0 = 0
#   10          - dataType = TYPE_INT_DEC (0x10)
#   XX 00 00 00 - data (little-endian int)
# So for value 33: 08 00 00 10 21 00 00 00

def find_typed_int(data, value):
    needle = struct.pack("<HBBi", 8, 0, 0x10, value)
    results = []
    offset = 0
    while True:
        idx = data.find(needle, offset)
        if idx == -1:
            break
        results.append(idx)
        offset = idx + 1
    return results

# Find all occurrences of typed int 33 (SDK 33)
hits = find_typed_int(manifest, 33)
print(f"Found typed int(33) at offsets: {hits}")

if not hits:
    # Also try dataType 0x11 (TYPE_INT_HEX)
    needle2 = struct.pack("<HBBi", 8, 0, 0x11, 33)
    hits = []
    offset = 0
    while True:
        idx = manifest.find(needle2, offset)
        if idx == -1:
            break
        hits.append(idx)
        offset = idx + 1
    print(f"Found typed int(33) with dataType=0x11 at offsets: {hits}")

if not hits:
    print("ERROR: Could not find typed integer value 33 in manifest.")
    print("Dumping all typed ints found:")
    # dump every typed int in the file for diagnosis
    i = 0
    while i < len(manifest) - 8:
        if manifest[i] == 8 and manifest[i+1] == 0 and manifest[i+2] == 0 and manifest[i+3] in (0x10, 0x11):
            val = struct.unpack_from("<I", manifest, i+4)[0]
            if val < 200:  # only small values (SDK versions are small numbers)
                print(f"  offset {i}: dataType={manifest[i+3]:#x} value={val}")
        i += 1
    sys.exit(1)

# Patch all hits (usually just one minSdkVersion)
for idx in hits:
    current = struct.unpack_from("<i", manifest, idx+4)[0]
    print(f"Patching offset {idx+4}: {current} -> {new_min}")
    struct.pack_into("<i", manifest, idx+4, new_min)

# Repack APK
tmp = apk_out + ".tmp"
with zipfile.ZipFile(apk_in, "r") as zin:
    with zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.infolist():
            if item.filename == "AndroidManifest.xml":
                item2 = zipfile.ZipInfo(item.filename)
                item2.compress_type = item.compress_type
                zout.writestr(item2, bytes(manifest))
            else:
                zout.writestr(item, zin.read(item.filename))

os.replace(tmp, apk_out)
print(f"Done: {apk_out}")
