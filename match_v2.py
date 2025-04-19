import os
import json
import shutil
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from sentence_transformers import SentenceTransformer, util

# --- CONFIGURATION ---
import config
import time
start_time = time.time()
print("Start Matching Module")

SOURCE_DIR = config.PULLED_ARTICLES_SAVE_DIR
DEST_DIR = config.MATCH_V2_DIR
SIMILARITY_THRESHOLD = 0.8
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# --- SETUP OUTPUT FOLDERS ---
os.makedirs(DEST_DIR, exist_ok=True)
not_matched_dir = os.path.join(DEST_DIR, "not_matched")
os.makedirs(not_matched_dir, exist_ok=True)

# --- LOAD AND FILTER ARTICLES ---
json_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".json")]
articles = []
file_paths = []

for filename in json_files:
    path = os.path.join(SOURCE_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
            content = data.get("content", "").strip()
            if content:
                articles.append(content)
                file_paths.append(path)
            else:
                shutil.copy(path, os.path.join(not_matched_dir, filename))
    except json.JSONDecodeError as e:
        print(f"⚠️ Skipping invalid JSON: {filename} ({str(e)})")
        shutil.copy(path, os.path.join(not_matched_dir, filename))

print(f"✅ Loaded {len(articles)} articles with non-empty content.")

# --- EMBED CONTENT USING SBERT ---
print("🔄 Generating embeddings...")
model = SentenceTransformer(MODEL_NAME)
embeddings = model.encode(articles, convert_to_tensor=True)

# --- COMPUTE COSINE SIMILARITY MATRIX ---
print("🔎 Calculating cosine similarities...")
similarity_matrix = util.pytorch_cos_sim(embeddings, embeddings).numpy()

# --- GROUP ARTICLES USING UNION-FIND ---
parent = list(range(len(articles)))

def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(x, y):
    root_x = find(x)
    root_y = find(y)
    if root_x != root_y:
        parent[root_y] = root_x

# --- PARALLEL SIMILARITY COMPARISON ---
def process_chunk(start, end):
    for i in range(start, end):
        for j in range(i + 1, len(articles)):
            if similarity_matrix[i][j] >= SIMILARITY_THRESHOLD:
                union(i, j)

print("🚀 Performing parallel similarity matching...")
num_threads = 8
chunk_size = len(articles) // num_threads + 1

with ThreadPoolExecutor(max_workers=num_threads) as executor:
    futures = []
    for t in range(num_threads):
        start = t * chunk_size
        end = min((t + 1) * chunk_size, len(articles))
        futures.append(executor.submit(process_chunk, start, end))
    for f in futures:
        f.result()  # Ensure all threads complete

# --- COLLECT GROUPS ---
groups = defaultdict(list)
for idx in range(len(articles)):
    group_id = find(idx)
    groups[group_id].append(idx)

# --- SAVE MATCHED GROUPS ---
matched_indices = set()
group_number = 1

for group_indices in groups.values():
    if len(group_indices) <= 1:
        continue  # skip singles (they go to not_matched)

    group_name = f"group_{group_number}"
    group_path = os.path.join(DEST_DIR, group_name)
    os.makedirs(group_path, exist_ok=True)

    print(f"\n📦 Matched {len(group_indices)} articles as {group_name}")
    for idx in group_indices:
        matched_indices.add(idx)
        src_path = file_paths[idx]
        shutil.copy(src_path, os.path.join(group_path, os.path.basename(src_path)))
        print(f"📁 Copied: {os.path.basename(src_path)} → {group_name}")

    group_number += 1

# --- HANDLE UNMATCHED ARTICLES ---
for idx in range(len(articles)):
    if idx not in matched_indices:
        src_path = file_paths[idx]
        shutil.copy(src_path, os.path.join(not_matched_dir, os.path.basename(src_path)))

print(f"\n✅ Done. Total groups created: {group_number - 1}")
print(f"📂 Unmatched articles saved to: {not_matched_dir}")

end_time = time.time()
elapsed_time = end_time - start_time
print(f"\n⏱️ Total execution time: {elapsed_time:.2f} seconds")
