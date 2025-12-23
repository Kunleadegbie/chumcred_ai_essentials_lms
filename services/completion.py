from services.certificates import issue_certificate


def finalize_if_completed(user):
    issue_certificate(user)
