########## Autocorrel8 ##########

## Project Vision ##
AutoCorrel8 is a forensic dashboard designed to assist investigators in analyzing digital evidence. 
The tool uses a modular interface capable of ingesting a wide array of file types, performing automated analysis,
and establishing correlations between different sources. 
The results are visualized to help investigators interpret the evidence and identify relationships across datasets.

## Proposed Tech Stack ##

# Core Fornesics and Network Analysis #
-Packet Inspection and network traffic analysis: Zeek
-Parsing Zeek logs into structured formats: ZAT (Zeek Analysis Tool)
-Data normalization, manipulation and correlation logic: Pandas (Python)
-File types: .pcap, .log, .evtx, .json, .csv, .xml, .txt, .db/.sqlite, .jpg/.png

# Backend Logic #
-Create modular components such as file parsers, anaylsis, correlation modules: Python

# Frontend and UI #
-Flutter/Dart: Create the dashboard interface

# Databases #
-SQlite: Store evidence data and analysis results.

