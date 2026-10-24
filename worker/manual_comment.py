import sys

from app.github_client import post_pr_comment


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m worker.manual_comment PR_NUMBER")
        sys.exit(1)

    pr_number = int(sys.argv[1])

    owner = "Qiuxiemou"
    repo = "ai-review-test"

    comment = (
        f"已收到 PR #{pr_number}，已记录本次提交。"
    )

    comment_id = post_pr_comment(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        comment=comment,
    )

    print(f"Comment published successfully! ID: {comment_id}")


if __name__ == "__main__":
    main()
