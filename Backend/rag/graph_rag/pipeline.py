from .chunker import DocumentChunker
from .graph_builder import GraphBuilder
import os
from pathlib import Path


def run_ingestion(data_dir: str = "rag/data"):
    part_files = [
        "part_1_conditions.md",
        "part_2_coping.md",
        "part_3_emotional.md",
        "part_4_lifestyle.md",
    ]

    builder = GraphBuilder()

    for i, filename in enumerate(part_files, 1):
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue

        print(f"\n=== Processing file {i}/4: {filename} ===")

        chunker = DocumentChunker(chunk_size=800, chunk_overlap=100)

        doc = chunker.load_single_file(filepath)
        if not doc:
            print(f"No content found in {filename}")
            continue

        chunks = chunker.chunk_documents([doc])
        print(f"Created {len(chunks)} chunks from {filename}")

        builder.build_graph(chunks)
        print(f"Completed processing {filename}")

    print("\n=== All files processed successfully ===")


if __name__ == "__main__":
    run_ingestion()
