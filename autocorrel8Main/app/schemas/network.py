# Schema for network packets
def core_fields(packet):
    return {
        "timestamp" : packet.get("timestamp"),
        "src_ip" : packet.get("src_ip"),
        "dst_ip" : packet.get("dst_ip"),
        "src_port" : packet.get("src_port"),
        "dst_port" : packet.get("dst_port"),
        "protocol" : packet.get("protocol"),
        "length" : packet.get("length"),
        "data" : packet.get("data")
    }
    
def layer_fields(packet):
    
    layers = {}
    
    if "dns" in packet:
        layers["dns"] = {
            "query" : packet["dns"].get("query"),
            "type" : packet["dns"].get("type"),
            "response" : packet["dns"].get("response")
        }
        
    if "http" in packet:
        layers["http"] = {
            "method" : packet["http"].get("method"),
            "host" : packet["http"].get("host"),
            "uri" : packet["http"].get("uri"),
            "user_agent" : packet["http"].get("user_agent"),
            "status_code" : packet["http"].get("status_code")
        }
        
    if "https" in packet:
        layers["https"] = {
            "method" : packet["http"].get("method"),
            "host" : packet["http"].get("host"),
            "uri" : packet["http"].get("uri"),
            "user_agent" : packet["http"].get("user_agent"),
            "status_code" : packet["http"].get("status_code")
        }
        
    
    if "tls" in packet:
        layers["tls"] = {
            "server_name" : packet["tls"].get("server_name"),
            "version" : packet["tls"].get("version"),
            "cipher_suite" : packet["tls"].get("cipher_suite")
        }
        
    if "tcp" in packet:
        layers["tcp"] = {
            "flags" : packet["tcp"].get("flags"),
            "window_size" : packet["tcp"].get("window_size"),
            "seq" : packet["tcp"].get("seq"),
        }
        
    if "udp" in packet:
        layers["udp"] = {
            "checksum" : packet["udp"].get("checksum"),
            "length" : packet["udp"].get("length"),
            "payload" : packet["udp"].get("payload")
        }
        
    if "icmp" in packet:
        layers["icmp"] = {
            "type" : packet["icmp"].get("type"),
            "code" : packet["icmp"].get("code"),
            "checksum" : packet["icmp"].get("checksum")
        }
        
    if "smb" in packet:
        layers["smb"] = {
            "command" : packet["smb"].get("command"),
            "status" : packet["smb"].get("status"),
            "flags" : packet["smb"].get("flags")
        }
        
    if "ftp" in packet:
        layers["ftp"] = {
            "command" : packet["ftp"].get("command"),
            "response_code" : packet["ftp"].get("response_code"),
            "data" : packet["ftp"].get("data")
        }
        
    return layers

def build_packet(packet):
    doc = core_fields(packet)
    doc["layers"] = layer_fields(packet)
    return doc