import 'package:flutter/material.dart';
import '../models/file_item.dart';

class FormatSelector extends StatelessWidget {
  final List<FormatOption> formats;
  final FormatOption? selectedFormat;
  final ValueChanged<FormatOption?> onFormatSelected;

  const FormatSelector({
    super.key,
    required this.formats,
    required this.selectedFormat,
    required this.onFormatSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (formats.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '选择目标格式',
          style: theme.textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: formats.map((format) {
            final isSelected = selectedFormat?.value == format.value;
            return ChoiceChip(
              label: Text(format.label),
              selected: isSelected,
              onSelected: (selected) {
                onFormatSelected(selected ? format : null);
              },
            );
          }).toList(),
        ),
      ],
    );
  }
}