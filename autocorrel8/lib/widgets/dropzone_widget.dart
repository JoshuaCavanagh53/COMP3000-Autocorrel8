import 'package:dotted_border/dotted_border.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dropzone/flutter_dropzone.dart';

class DropzoneWidget extends StatefulWidget {
  @override
  _DropzoneWidgetState createState() => _DropzoneWidgetState();
}

class _DropzoneWidgetState extends State<DropzoneWidget> {
  
  late DropzoneViewController controller;
  
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.blue,
      width: 200,
      height: 200,
      child: Stack(
        children: [
          DropzoneView(
            onCreated: (controller) => this.controller = controller,
            onDropFile: acceptFile),
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.cloud_upload, size: 80, color: Colors.white),
                Text(
                  'Drop Files Here',
                  style: TextStyle(color: Colors.white, fontSize: 24),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

   Future acceptFile(dynamic event) async {
    final name = event.name;

    print('Name: $name');
   }
}
