"""Extract clean text from Project Gutenberg raw file into original.md."""
import sys

def main():
    src = sys.argv[1]
    dst = sys.argv[2]

    with open(src, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    start = None
    end = None
    for i, line in enumerate(lines):
        if "*** START OF THE PROJECT GUTENBERG EBOOK" in line:
            start = i + 1
        if "*** END OF THE PROJECT GUTENBERG EBOOK" in line:
            end = i

    if start is None or end is None:
        print("ERROR: Could not find Gutenberg markers")
        sys.exit(1)

    content = "".join(lines[start:end]).strip()

    with open(dst, "w", encoding="utf-8") as f:
        f.write(content)
        f.write("\n")

    print(f"Created {dst} with {len(content)} characters ({end - start} lines)")


if __name__ == "__main__":
    main()
