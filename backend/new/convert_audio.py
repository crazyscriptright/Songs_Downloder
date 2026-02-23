"""CLI tool for audio format conversion"""
import sys
import os
import argparse
from modules.audio_converter import AudioConverter

def main():
    parser = argparse.ArgumentParser(
        description='Convert audio files between formats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  python convert_audio.py input.flac output.mp3 --bitrate 320k

  python convert_audio.py input.flac output.aac --format aac --bitrate 256k

  python convert_audio.py input.flac output.mp3 --vbr 0

  python convert_audio.py --input-dir ./flac_files --output-dir ./mp3_files --format mp3

  python convert_audio.py --info input.flac

Supported formats: mp3, aac, m4a, ogg, opus, flac, wav
        """
    )

    parser.add_argument('input', nargs='?', help='Input audio file')
    parser.add_argument('output', nargs='?', help='Output audio file')

    parser.add_argument('--format', '-f',
                       choices=['mp3', 'aac', 'm4a', 'ogg', 'opus', 'flac', 'wav'],
                       help='Output format (auto-detected from output file extension)')

    parser.add_argument('--bitrate', '-b',
                       help='Target bitrate (e.g., 320k, 192k, 128k)')

    parser.add_argument('--vbr', type=int,
                       help='Variable bitrate quality (MP3: 0-9, AAC: 1-5, OGG: 1-10)')

    parser.add_argument('--sample-rate', '-s', type=int,
                       help='Target sample rate in Hz (e.g., 44100, 48000)')

    parser.add_argument('--overwrite', '-y', action='store_true',
                       help='Overwrite output file if exists')

    parser.add_argument('--no-metadata', action='store_true',
                       help='Do not preserve metadata')

    parser.add_argument('--info', '-i', action='store_true',
                       help='Show audio file information')

    parser.add_argument('--input-dir', help='Directory containing input files')
    parser.add_argument('--output-dir', help='Directory for output files')

    args = parser.parse_args()

    try:
        converter = AudioConverter()

        if args.info:
            if not args.input:
                print("Error: Please specify input file")
                sys.exit(1)

            info = converter.get_audio_info(args.input)
            print(f"\n{'='*60}")
            print(f"Audio File Information: {os.path.basename(args.input)}")
            print(f"{'='*60}")
            print(f"  Format:       {info['format']}")
            print(f"  Codec:        {info['codec']}")
            print(f"  Bitrate:      {info['bitrate']} kbps")
            print(f"  Sample Rate:  {info['sample_rate']} Hz")
            print(f"  Channels:     {info['channels']}")
            print(f"  Duration:     {info['duration']:.2f} seconds")
            print(f"  File Size:    {info['size'] / (1024*1024):.2f} MB")
            print(f"{'='*60}\n")
            return

        if args.input_dir:
            if not args.output_dir:
                print("Error: --output-dir required for batch conversion")
                sys.exit(1)

            if not args.format:
                print("Error: --format required for batch conversion")
                sys.exit(1)

            audio_extensions = ['.flac', '.mp3', '.aac', '.m4a', '.ogg', '.opus', '.wav']
            input_files = []

            for root, dirs, files in os.walk(args.input_dir):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in audio_extensions):
                        input_files.append(os.path.join(root, file))

            if not input_files:
                print(f"No audio files found in {args.input_dir}")
                sys.exit(1)

            print(f"\nFound {len(input_files)} audio files")
            print(f"Converting to {args.format.upper()}...\n")

            results = converter.convert_batch(
                input_files,
                args.output_dir,
                args.format,
                bitrate=args.bitrate,
                vbr_quality=args.vbr,
                sample_rate=args.sample_rate,
                preserve_metadata=not args.no_metadata,
                overwrite=args.overwrite
            )

            print(f"\n{'='*60}")
            print(f"Batch Conversion Complete")
            print(f"{'='*60}")
            print(f"  Success: {len(results['success'])} files")
            print(f"  Failed:  {len(results['failed'])} files")
            print(f"{'='*60}\n")

            if results['failed']:
                print("Failed files:")
                for file, error in results['failed']:
                    print(f"  ✗ {os.path.basename(file)}: {error}")

            return

        if not args.input or not args.output:
            parser.print_help()
            sys.exit(1)

        output_format = args.format
        if not output_format:
            ext = os.path.splitext(args.output)[1].lstrip('.')
            if ext in AudioConverter.FORMATS:
                output_format = ext
            else:
                print(f"Error: Unknown output format '{ext}'. Use --format to specify")
                sys.exit(1)

        converter.convert(
            args.input,
            args.output,
            output_format,
            bitrate=args.bitrate,
            vbr_quality=args.vbr,
            sample_rate=args.sample_rate,
            preserve_metadata=not args.no_metadata,
            overwrite=args.overwrite
        )

        print("\n✓ Conversion successful!\n")

    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}\n")
        sys.exit(1)
    except FileExistsError as e:
        print(f"\n✗ Error: {e}")
        print("Use --overwrite (-y) to replace existing file\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
