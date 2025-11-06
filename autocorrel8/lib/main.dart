import 'package:flutter/material.dart';
import 'widgets/dropzone_widget.dart';

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
          child: DropzoneWidget(),
        ),
      ),
    );
  }
}
