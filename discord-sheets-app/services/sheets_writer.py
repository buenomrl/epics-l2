import os
import time
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HISTORY_SHEET = "Histórico"
SUMMARY_SHEET = "Resumo"
HISTORY_HEADER = ["Data", "Boss", "CP", "Nº Membros", "Membros"]
MEMBERS_SHEET = "Participações"
MEMBERS_HEADER = ["CP", "Membro", "Participações"]


def _get_workbook():
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    sheet_id = os.getenv("GOOGLE_SHEETS_ID", "")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_ID não configurado no .env")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(sheet_id)


def _get_or_create_history(wb):
    try:
        ws = wb.worksheet(HISTORY_SHEET)
    except gspread.WorksheetNotFound:
        ws = wb.add_worksheet(HISTORY_SHEET, rows=1000, cols=10)
    if not ws.get_all_values():
        ws.append_row(HISTORY_HEADER)
    return ws


def _rebuild_summary(wb):
    """Reconstrói o Resumo do zero lendo o Histórico completo."""
    try:
        history_ws = wb.worksheet(HISTORY_SHEET)
    except gspread.WorksheetNotFound:
        return

    history_data = history_ws.get_all_values()
    # Pula só linhas que são cabeçalho real ou vazias; inclui todas as linhas de dados
    rows_data = [
        r for r in history_data
        if len(r) >= 4 and r[0] and r[0] != "Data" and r[2] and not r[2].startswith("⚠")
    ]

    if not rows_data:
        return

    # Monta estrutura: ordem dos eventos e contagem por CP
    event_order = []
    cp_event_counts: dict[str, dict[str, int]] = {}

    for row in rows_data:
        date, boss, cp, n_members = row[0], row[1], row[2], row[3]
        event = f"{boss} {date}"
        if event not in event_order:
            event_order.append(event)
        count = int(n_members or 0)
        cp_event_counts.setdefault(cp, {})[event] = cp_event_counts.get(cp, {}).get(event, 0) + count

    # Monta cabeçalho e linhas
    headers = ["CP"] + event_order + ["TOTAL"]
    result_rows = [headers]
    for cp in sorted(cp_event_counts):
        row = [cp]
        total = 0
        for event in event_order:
            count = cp_event_counts[cp].get(event, 0)
            row.append(count)
            total += count
        row.append(total)
        result_rows.append(row)

    # Escreve no Resumo
    try:
        summary_ws = wb.worksheet(SUMMARY_SHEET)
    except gspread.WorksheetNotFound:
        summary_ws = wb.add_worksheet(SUMMARY_SHEET, rows=200, cols=60)

    summary_ws.clear()
    time.sleep(1)
    summary_ws.update(range_name="A1", values=result_rows)
    _format_summary(summary_ws, len(headers))


def _format_summary(ws, n_cols: int):
    try:
        last_col = chr(ord("A") + min(n_cols - 1, 25))
        ws.format(f"A1:{last_col}1", {
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "backgroundColor": {"red": 0.13, "green": 0.13, "blue": 0.25}
        })
        ws.format("A2:A200", {"textFormat": {"bold": True}})
    except Exception:
        pass


def _rebuild_member_stats(wb):
    """Reconstrói a aba Participações contando quantos boss kills cada membro tem por CP."""
    from services.cp_tracker import load_cp_list_full

    try:
        history_ws = wb.worksheet(HISTORY_SHEET)
    except gspread.WorksheetNotFound:
        return

    history_data = history_ws.get_all_values()
    rows_data = [
        r for r in history_data
        if len(r) >= 5 and r[0] and r[0] != "Data" and r[2]
    ]

    if not rows_data:
        return

    # Contagem por (cp, membro) — "⚠ Não identificado" vira "Sem CP"
    counts: dict[tuple[str, str], int] = {}
    for row in rows_data:
        cp = row[2].strip()
        if cp.startswith("⚠"):
            cp = "Sem CP"
        members_raw = row[4] if len(row) > 4 else ""
        for member in members_raw.split(","):
            member = member.strip()
            if member:
                key = (cp, member)
                counts[key] = counts.get(key, 0) + 1

    # Adiciona membros do CP List com 0 participações se nunca apareceram
    _svc_dir = os.path.dirname(os.path.abspath(__file__))
    _epics_dir = os.path.dirname(os.path.dirname(_svc_dir))
    cp_list_path = os.getenv("CP_LIST_PATH", os.path.join(_epics_dir, "CP List.txt"))
    if os.path.exists(cp_list_path):
        counted_uppers = {m.upper() for (_, m) in counts}
        for original_name, cp in load_cp_list_full(cp_list_path):
            if original_name.upper() not in counted_uppers:
                counts[(cp, original_name)] = 0

    # Ordena: CP alfabético ("Sem CP" sempre no final), depois por participações desc, depois nome asc
    sorted_entries = sorted(
        counts.items(),
        key=lambda x: (x[0][0] == "Sem CP", x[0][0], -x[1], x[0][1])
    )
    result_rows = [MEMBERS_HEADER] + [[cp, member, count] for (cp, member), count in sorted_entries]

    try:
        ws = wb.worksheet(MEMBERS_SHEET)
    except gspread.WorksheetNotFound:
        ws = wb.add_worksheet(MEMBERS_SHEET, rows=1000, cols=5)

    ws.clear()
    time.sleep(1)
    ws.update(range_name="A1", values=result_rows)

    try:
        ws.format("A1:C1", {
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "backgroundColor": {"red": 0.13, "green": 0.13, "blue": 0.25}
        })
    except Exception:
        pass


def save_attendance(boss: str, date: str, attendance: list) -> dict:
    wb = _get_workbook()
    ws = _get_or_create_history(wb)

    cp_groups: dict[str, list] = {}
    not_found: list = []

    for entry in attendance:
        cp = entry.get("cp", "").strip()
        member = entry.get("member", "").strip()
        if not member:
            continue
        if cp:
            cp_groups.setdefault(cp, []).append(member)
        else:
            not_found.append(member)

    # Salva no Histórico
    rows = []
    for cp, members in sorted(cp_groups.items()):
        rows.append([date, boss, cp, len(members), ", ".join(members)])
    if not_found:
        rows.append([date, boss, "⚠ Não identificado", len(not_found), ", ".join(not_found)])
    if rows:
        ws.append_rows(rows)

    # Reconstrói Resumo e Participações a partir do Histórico
    _rebuild_summary(wb)
    _rebuild_member_stats(wb)

    return {"cps_saved": len(cp_groups), "not_found": not_found}
