import os
import math
from collections import Counter

def shannon_entropy(data):
    """
    Calculates the Shannon Entropy of the data.
    Higher entropy (close to 8.0) means the data is already compressed/encrypted.
    Lower entropy means it is highly compressible.
    """
    if not data:
        return 0
    entropy = 0
    counts = Counter(data)
    for count in counts.values():
        p_x = count / len(data)
        entropy -= p_x * math.log2(p_x)
    return entropy

def sample_features(file_path, sample_kb=64):
    """
    Analyzes a file using statistical heuristics to predict the best compression strategy.
    """
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        return None
        
    size = os.path.getsize(file_path)
    # If the file is smaller than our sample size, just read the whole thing
    read_size = min(size, sample_kb * 1024)
    
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(read_size)
    except Exception:
        return None
    
    if not sample:
        return {'entropy': 0, 'size_bytes': size, 'is_text': False, 'repetition': 0, 'compressible': False}

    # 1. Calculate Shannon Entropy (0.0 to 8.0)
    entropy = shannon_entropy(sample)
    
    # 2. Structural Repetition (4-byte sliding window)
    # This detects patterns like recurring headers in CSVs or logs
    chunks = [sample[i:i+4] for i in range(0, len(sample) - 3, 4)]
    if chunks:
        unique_chunks = len(set(chunks))
        repetition_ratio = 1.0 - (unique_chunks / len(chunks))
    else:
        repetition_ratio = 0
    
    # 3. Robust Text vs Binary detection
    # Checks for printable characters (ASCII) vs Null bytes/Control codes
    null_count = sample.count(0)
    text_chars = sum(1 for c in sample if 32 <= c <= 126 or c in (9,10,13))
    text_ratio = text_chars / len(sample)
    
    # Heuristic for text: High printable ratio AND low null-byte count
    is_text = text_ratio > 0.8 and null_count < (len(sample) * 0.01)
    
    # 4. Final Compressibility Heuristic
    # If entropy is > 7.5, the file is likely already a ZIP, JPG, or Encrypted.
    is_compressible = entropy < 7.5 or repetition_ratio > 0.1

    return {
        'entropy': round(entropy, 2),
        'size_bytes': size,
        'size_mb': round(size / (1024 * 1024), 2),
        'is_text': is_text,
        'repetition': round(repetition_ratio, 4),
        'compressible': is_compressible,
        'magic': sample[:8].hex().upper()
    }