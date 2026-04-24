from email.header import decode_header


def decode_header_value(header: str) -> str:
    if not header:
        return ""

    parts = decode_header(header)
    result = []

    for content, encoding in parts:
        if isinstance(content, bytes):
            result.append(content.decode(encoding or "utf-8", errors="ignore"))
        else:
            result.append(content)

    return " ".join(result)


def get_email_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except:
            pass

    return ""