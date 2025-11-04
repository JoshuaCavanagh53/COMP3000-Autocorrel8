import 'package:flutter/material.dart';

void main() => runApp(const MainApp());

class MainApp extends StatelessWidget {
  const MainApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(
          title: const Text('AutoCorrel8 Dashboard'),
        ),
        body: Center( 
          child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Draggable Evidence Card
            Draggable<String>(
              data: 'PCAP_File_001',
              feedback: Material(
                child: Container(
                  width: 120,
                  height: 50,
                  color: Colors.blueAccent,
                  child: const Center(
                    child: Text(
                      'Dragging Evidence',
                      style: TextStyle(color: Colors.white),
                    ),
                  ),
                ),
              ),
              childWhenDragging: Container(
                width: 120,
                height: 50,
                color: Colors.grey,
                child: const Center(
                  child: Text('Evidence Dragged'),
                ),
              ),
              child: Container(
                width: 120,
                height: 50,
                color: Colors.green,
                child: const Center(
                  child: Text(
                    'PCAP_File_001',
                    style: TextStyle(color: Colors.white),
                  ),
                ),
              ),
            ),

            const SizedBox(height: 40),

            // Drop Zone
            DragTarget<String>(
              onAccept: (data) {
                print('Dropped: $data');
              },
              builder: (context, candidateData, rejectedData) {
                return Container(
                  width: 200,
                  height: 150,
                  decoration: BoxDecoration(
                    color: candidateData.isNotEmpty ? Colors.green : Colors.grey,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Center(
                    child: Text(
                      'Drop Evidence Here',
                      style: TextStyle(color: Colors.white),
                    ),
                  ),
                );
              },
            ),
          ],
        ),
      ),
      ),
    );
  }
}
