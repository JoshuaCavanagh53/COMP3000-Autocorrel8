from schemas import normalized_schema
from datetime import datetime

def create_network_object_from_zeek(row):
    # Instantiate normalized object
    obj = normalized_schema.create_normalized_event()
    # Define each fields using outputs from the zeek parsing
    obj["source"] = "zeek_conn"
    obj["event_type"] = "network_connection"
    obj["timestamp"] = datetime.utcfromtimestamp(float(row["ts"])).isoformat() + "Z"
    obj["host"]["ip"] = row["id.orig_h"]
    obj["network"] = {
        "src_ip": row["id.orig_h"],
        "src_port": int(row["id.orig_p"]),
        "dst_ip": row["id.resp_h"],
        "dst_port": int(row["id.resp_p"]),
        "protocol": row["proto"],
        "service": row.get("service", "")
    }
    obj["details"] = {
        "duration": float(row.get("duration", 0)),
        "bytes_sent": int(row.get("orig_bytes", 0)),
        "bytes_received": int(row.get("resp_bytes", 0)),
        "conn_state": row.get("conn_state", "")
    }
    obj["tags"] = ["network", row.get("proto", "").lower()]
    return obj