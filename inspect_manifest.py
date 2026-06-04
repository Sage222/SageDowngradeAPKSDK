import zipfile, struct, sys

apk_path = sys.argv[1]

with zipfile.ZipFile(apk_path, 'r') as z:
    manifest = z.read('AndroidManifest.xml')

data = bytearray(manifest)

# Known attribute IDs for SDK version fields
ATTRS = {
    0x0101021b: 'minSdkVersion',
    0x01010270: 'targetSdkVersion', 
    0x01010271: 'maxSdkVersion',
}

print(f"Manifest size: {len(data)} bytes")
print()

# Scan for all attribute ID occurrences
for attr_id, attr_name in ATTRS.items():
    needle = struct.pack('<I', attr_id)
    offset = 0
    while True:
        idx = data.find(needle, offset)
        if idx == -1:
            break
        # data value is 16 bytes after the attribute name field
        data_offset = idx + 16
        if data_offset + 4 <= len(data):
            val = struct.unpack_from('<I', data, data_offset)[0]
            print(f"  {attr_name} (0x{attr_id:08x}) @ offset {idx}: value = {val} (0x{val:08x})")
        offset = idx + 1

# Also dump raw bytes around each find for verification
print()
print("Raw hex around minSdkVersion attribute:")
needle = struct.pack('<I', 0x0101021b)
idx = data.find(needle)
if idx != -1:
    start = max(0, idx-4)
    end = min(len(data), idx+24)
    chunk = data[start:end]
    hex_str = ' '.join(f'{b:02x}' for b in chunk)
    print(f"  offset {start}: {hex_str}")
