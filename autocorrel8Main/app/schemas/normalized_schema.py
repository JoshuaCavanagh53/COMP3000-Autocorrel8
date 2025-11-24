from pydantic import BaseModel, Field
from typing import Optional, Dict

# This schema defines a normalized structure for various log/event records
# to facilitate uniform processing and analysis across different data sources.
class NormalizedRecord(BaseModel):
    record_id: Optional[str] = Field(None, description="Unique identifier for the record")
    timestamp: str = Field(..., description="Timestamp in ISO 8601 format")
    source: Optional[str] = Field(None, description="Log source (e.g., zeek_conn, syslog, registry)")
    event_type: Optional[str] = Field(None, description="Normalized event type (e.g., network_connection, process_start, registry_change)")
    
    # Host/User context
    hostname: Optional[str] = Field(None, description="Host where the event occurred")
    host_ip: Optional[str] = Field(None, description="IP of the host")
    username: Optional[str] = Field(None, description="Username associated with the event")
    user_domain: Optional[str] = Field(None, description="Domain of the user if applicable")
    
    # Network fields
    source_ip: Optional[str] = Field(None, description="Source IP address")
    destination_ip: Optional[str] = Field(None, description="Destination IP address")
    source_port: Optional[int] = Field(None, description="Source port number")
    destination_port: Optional[int] = Field(None, description="Destination port number")
    protocol: Optional[str] = Field(None, description="Network protocol used")
    
    # System fields
    process_name: Optional[str] = Field(None, description="Name of the process involved")
    file_path: Optional[str] = Field(None, description="Path of the file accessed or modified")
    
    # Registry fields
    registry_key: Optional[str] = Field(None, description="Registry key involved in the event")
    
    # General metadata
    severity: Optional[str] = Field(None, description="Severity level (info, warning, critical)")
    outcome: Optional[str] = Field(None, description="Outcome of the event (success, failure)")
    details: Optional[Dict] = Field(None, description="Additional structured information relevant to the record")
