import json
import struct

def write_container(header: dict, compressed_bytes: bytes, out_path, crypto_data=None):
    """
    header: Dictionary containing tool info, etc.
    crypto_data: Optional dict with {'nonce': bytes, 'tag': bytes}
    """
    # If we have encryption data, add it to the header
    if crypto_data:
        header['encryption'] = {
            'nonce': crypto_data['nonce'].hex(),
            'tag': crypto_data['tag'].hex()
        }
    
    header_json = json.dumps(header).encode('utf-8')
    
    with open(out_path, 'wb') as f:
        # 4-byte big-endian length of the header
        f.write(struct.pack('>I', len(header_json)))
        f.write(header_json)
        f.write(compressed_bytes)

def read_container(path):
    with open(path, 'rb') as f:
        # Read the 4-byte header length
        raw_len = f.read(4)
        if not raw_len:
            return None, None
            
        header_len = struct.unpack('>I', raw_len)[0]
        header_bytes = f.read(header_len)
        header = json.loads(header_bytes.decode('utf-8'))
        
        # Everything else is the encrypted/compressed payload
        payload = f.read()
        
    return header, payload