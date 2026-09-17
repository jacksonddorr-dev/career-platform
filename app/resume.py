from fastapi.responses import Response

from app.content import PublicProfile


def resume_response(content: PublicProfile) -> Response:
    p = content.profile
    lines = [p.full_name, p.headline, p.email, p.location, "", p.summary, ""]
    if content.experience:
        lines.append("EXPERIENCE")
        for item in content.experience:
            lines.extend([f"{item.title} — {item.company_name}", item.summary])
            lines.extend(f"• {a.text}" for a in item.achievements)
    if content.projects:
        lines.append("\nPROJECTS")
        for item in content.projects:
            lines.extend([item.title, item.short_description])
            lines.extend(f"• {h.text}" for h in item.highlights)
    if content.skill_categories:
        lines.append("\nSKILLS")
        lines.extend(f"{category.name}: {', '.join(s.name for s in category.skills)}" for category in content.skill_categories)
    if content.education:
        lines.append("\nEDUCATION")
        lines.extend(f"{item.degree_name} — {item.institution_name}" for item in content.education)
    text = "\n".join(lines).strip().splitlines()
    commands = ["BT", "/F1 11 Tf", "72 760 Td"]
    for index, line in enumerate(text[:48]):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index:
            commands.append("0 -16 Td")
        commands.append(f"({safe[:140]}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    pdf.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return Response(bytes(pdf), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="resume.pdf"'})
