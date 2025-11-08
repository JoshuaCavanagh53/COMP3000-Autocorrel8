# This is a normalized schema used for all my file uploads
# Files are inputed through the parsers and filled into an instance of this object, filling in relevant fields.
def create_normalized_event():
    return {
        "source": "",            
        "event_type": "",      
        "timestamp": "",           
        "host": {
            "hostname": "",
            "ip": "",
            "user": ""
        },
        # If file is a network log , Zeek is used to parse the data and data is fed into this section
        "network": {
            "src_ip": "",
            "src_port": 0,
            "dst_ip": "",
            "dst_port": 0,
            "protocol": "",
            "service": ""
        },
        # If the file is a browser history log, my own logic is used to parse data into the relevant fields
        "browser": {
            "url": "",
            "title": "",
            "referrer": "",
            "user_agent": "",
            "visit_count": 0
        },
        # If the file is a system log, my own logic is used to parse the data into the relevant fields
        "system": {
            "process_name": "",
            "pid": 0,
            "event": "",
            "message": "",
            "severity": ""
        },
        # These are optional extra fields that can have additional data filled into them
        "details": {},             
        "tags": [],                    
    }
