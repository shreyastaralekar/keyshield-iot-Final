"""Schema of the CICIoT2023 MERGED_CSV files (39 features + Label) and the label -> category mapping."""
from __future__ import annotations

FEATURES = [
    "Header_Length", "Protocol Type", "Time_To_Live", "Rate",
    "fin_flag_number", "syn_flag_number", "rst_flag_number", "psh_flag_number",
    "ack_flag_number", "ece_flag_number", "cwr_flag_number",
    "ack_count", "syn_count", "fin_count", "rst_count",
    "HTTP", "HTTPS", "DNS", "Telnet", "SMTP", "SSH", "IRC",
    "TCP", "UDP", "DHCP", "ARP", "ICMP", "IGMP", "IPv", "LLC",
    "Tot sum", "Min", "Max", "AVG", "Std", "Tot size", "IAT", "Number", "Variance",
]
LABEL_COL = "Label"
BENIGN = "BENIGN"
BENIGN_CAT = "Benign"

# The 7 attack categories of the dataset paper
CATEGORIES = ["DDoS", "DoS", "Mirai", "Recon", "Spoofing", "WebBased", "BruteForce"]

_SPOOFING = {"MITM-ARPSPOOFING", "DNS_SPOOFING"}
_WEB = {"BROWSERHIJACKING", "COMMANDINJECTION", "XSS", "SQLINJECTION", "BACKDOOR_MALWARE", "UPLOADING_ATTACK"}
_BRUTE = {"DICTIONARYBRUTEFORCE"}


def label_to_category(label: str) -> str:
    """Map a raw label (e.g. 'DDOS-SYN_FLOOD') to one of the 7 categories, 'Benign', or 'Unknown'."""
    l = str(label).strip().upper()
    if l == BENIGN:
        return BENIGN_CAT
    if l.startswith("DDOS-"):
        return "DDoS"
    if l.startswith("DOS-"):
        return "DoS"
    if l.startswith("MIRAI-"):
        return "Mirai"
    if l.startswith("RECON-") or l == "VULNERABILITYSCAN":
        return "Recon"
    if l in _SPOOFING:
        return "Spoofing"
    if l in _BRUTE:
        return "BruteForce"
    if l in _WEB:
        return "WebBased"
    return "Unknown"
