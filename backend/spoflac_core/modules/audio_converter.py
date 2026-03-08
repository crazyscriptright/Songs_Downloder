"""Audio format converter using FFmpeg"""
import os
import subprocess
import shutil
from typing import Optional


class AudioConverter:
    """Convert audio files between formats with configurable quality"""
    
    # Supported formats and their default parameters
    FORMATS = {
        'mp3': {
            'codec': 'libmp3lame',
            'bitrates': ['128k', '192k', '256k', '320k'],
            'default_bitrate': '320k',
            'vbr_quality': [0, 2, 4, 6, 9]  # 0=highest, 9=lowest
        },
        'aac': {
            'codec': 'aac',
            'bitrates': ['128k', '192k', '256k', '320k'],
            'default_bitrate': '256k',
            'vbr_quality': [0.1, 0.3, 0.5, 0.7, 0.9]
        },
        'm4a': {
            'codec': 'aac',
            'bitrates': ['128k', '192k', '256k', '320k'],
            'default_bitrate': '256k',
            'vbr_quality': [0.1, 0.3, 0.5, 0.7, 0.9]
        },
        'ogg': {
            'codec': 'libvorbis',
            'bitrates': ['128k', '192k', '256k', '320k'],
            'default_bitrate': '256k',
            'vbr_quality': [1, 3, 5, 7, 10]  # 1=lowest, 10=highest
        },
        'opus': {
            'codec': 'libopus',
            'bitrates': ['96k', '128k', '192k', '256k', '320k'],
            'default_bitrate': '192k',
            'vbr_quality': None
        },
        'flac': {
            'codec': 'flac',
            'bitrates': None,  # Lossless
            'default_bitrate': None,
            'compression_level': [0, 5, 8, 12]  # 0=fast, 12=best compression
        },
        'wav': {
            'codec': 'pcm_s16le',
            'bitrates': None,  # Lossless
            'default_bitrate': None,
            'vbr_quality': None
        }
    }
    
    def __init__(self):
        """Initialize converter and check for FFmpeg"""
        self.ffmpeg_path = self._find_ffmpeg()
        if not self.ffmpeg_path:
            raise Exception("FFmpeg not found. Install FFmpeg and add to PATH")
    
    @staticmethod
    def _find_ffmpeg() -> Optional[str]:
        """Find FFmpeg executable in PATH"""
        return shutil.which('ffmpeg')
    
    def convert(
        self,
        input_file: str,
        output_file: str,
        output_format: str = 'mp3',
        bitrate: str = None,
        vbr_quality: int = None,
        sample_rate: int = None,
        preserve_metadata: bool = True,
        overwrite: bool = False
    ) -> bool:
        """Convert audio file to specified format
        
        Args:
            input_file: Path to input audio file
            output_file: Path to output audio file
            output_format: Target format (mp3, aac, m4a, ogg, opus, flac, wav)
            bitrate: Target bitrate (e.g., '320k', '192k'). If None, uses default
            vbr_quality: Variable bitrate quality (format-specific scale)
            sample_rate: Target sample rate in Hz (e.g., 44100, 48000)
            preserve_metadata: Copy metadata from input to output
            overwrite: Overwrite output file if exists
            
        Returns:
            True if conversion successful, False otherwise
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        output_format = output_format.lower().lstrip('.')
        
        if output_format not in self.FORMATS:
            raise ValueError(f"Unsupported format: {output_format}. Supported: {', '.join(self.FORMATS.keys())}")
        
        # Check if output file exists
        if os.path.exists(output_file) and not overwrite:
            raise FileExistsError(f"Output file already exists: {output_file}")
        
        # Build FFmpeg command
        cmd = [self.ffmpeg_path, '-i', input_file]
        
        # Overwrite flag
        if overwrite:
            cmd.append('-y')
        else:
            cmd.append('-n')
        
        # Set codec
        format_config = self.FORMATS[output_format]
        cmd.extend(['-c:a', format_config['codec']])
        
        # Set quality parameters
        if output_format == 'flac':
            # FLAC compression level (0-12)
            compression = 8  # Default
            cmd.extend(['-compression_level', str(compression)])
            
        elif output_format in ['wav']:
            # PCM - no additional quality settings needed
            pass
            
        elif vbr_quality is not None:
            # Variable Bitrate
            if output_format == 'mp3':
                cmd.extend(['-q:a', str(vbr_quality)])  # 0-9 (0=best)
            elif output_format in ['aac', 'm4a']:
                cmd.extend(['-vbr', str(vbr_quality)])  # 1-5
            elif output_format == 'ogg':
                cmd.extend(['-q:a', str(vbr_quality)])  # 1-10 (10=best)
                
        else:
            # Constant Bitrate
            if bitrate is None:
                bitrate = format_config['default_bitrate']
            
            if bitrate:
                cmd.extend(['-b:a', bitrate])
        
        # Set sample rate if specified
        if sample_rate:
            cmd.extend(['-ar', str(sample_rate)])
        
        # Preserve metadata
        if preserve_metadata:
            cmd.extend(['-map_metadata', '0'])
            cmd.extend(['-id3v2_version', '3'])
        
        # Set output format explicitly
        if output_format == 'm4a':
            cmd.extend(['-f', 'ipod'])
        elif output_format == 'ogg':
            cmd.extend(['-f', 'ogg'])
        
        # Output file
        cmd.append(output_file)
        
        # Execute FFmpeg
        try:
            print(f"Converting {os.path.basename(input_file)} → {output_format.upper()} ({bitrate or 'VBR'})")
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr
                # Check for common errors
                if 'already exists' in error_msg:
                    raise FileExistsError(f"Output file exists: {output_file}")
                else:
                    raise Exception(f"FFmpeg error: {error_msg[-500:]}")
            
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file) / (1024 * 1024)
                print(f" Conversion complete: {output_file} ({file_size:.2f} MB)")
                return True
            else:
                raise Exception("Conversion failed: Output file not created")
                
        except subprocess.TimeoutExpired:
            raise Exception("Conversion timed out (>5 minutes)")
        except Exception as e:
            raise Exception(f"Conversion failed: {e}")
    
    def convert_batch(
        self,
        input_files: list,
        output_dir: str,
        output_format: str = 'mp3',
        **kwargs
    ) -> dict:
        """Convert multiple files
        
        Args:
            input_files: List of input file paths
            output_dir: Directory for output files
            output_format: Target format
            **kwargs: Additional arguments passed to convert()
            
        Returns:
            Dictionary with 'success' and 'failed' lists
        """
        os.makedirs(output_dir, exist_ok=True)
        
        results = {'success': [], 'failed': []}
        
        for input_file in input_files:
            try:
                basename = os.path.splitext(os.path.basename(input_file))[0]
                output_file = os.path.join(output_dir, f"{basename}.{output_format}")
                
                self.convert(input_file, output_file, output_format, **kwargs)
                results['success'].append(input_file)
                
            except Exception as e:
                print(f" Failed to convert {input_file}: {e}")
                results['failed'].append((input_file, str(e)))
        
        return results
    
    def get_audio_info(self, file_path: str) -> dict:
        """Get audio file information using FFprobe
        
        Returns:
            Dictionary with codec, bitrate, sample_rate, duration, format
        """
        ffprobe_path = shutil.which('ffprobe')
        if not ffprobe_path:
            raise Exception("FFprobe not found")
        
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception("FFprobe failed")
            
            import json
            data = json.loads(result.stdout)
            
            # Extract audio stream info
            audio_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                raise Exception("No audio stream found")
            
            format_info = data.get('format', {})
            
            return {
                'codec': audio_stream.get('codec_name'),
                'bitrate': int(audio_stream.get('bit_rate', 0)) // 1000,  # kbps
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': audio_stream.get('channels'),
                'duration': float(format_info.get('duration', 0)),
                'format': format_info.get('format_name'),
                'size': int(format_info.get('size', 0))
            }
            
        except Exception as e:
            raise Exception(f"Failed to get audio info: {e}")


def convert_to_mp3(input_file: str, output_file: str, bitrate: str = '320k', **kwargs):
    """Quick converter to MP3 with specified bitrate"""
    converter = AudioConverter()
    return converter.convert(input_file, output_file, 'mp3', bitrate=bitrate, **kwargs)


def convert_to_format(input_file: str, output_file: str, format: str, **kwargs):
    """Quick converter to any supported format"""
    converter = AudioConverter()
    return converter.convert(input_file, output_file, format, **kwargs)


if __name__ == '__main__':
    # Test/Example usage
    converter = AudioConverter()
    
    # Example conversions
    # converter.convert('input.flac', 'output.mp3', 'mp3', bitrate='320k')
    # converter.convert('input.flac', 'output.aac', 'aac', bitrate='256k')
    # converter.convert('input.mp3', 'output.flac', 'flac')  # Lossy to lossless
    # converter.convert('input.flac', 'output.mp3', 'mp3', vbr_quality=0)  # VBR V0
    
    # Get file info
    # info = converter.get_audio_info('input.flac')
    # print(f"Codec: {info['codec']}, Bitrate: {info['bitrate']}kbps")
    
    print("AudioConverter module ready")
    print(f"Supported formats: {', '.join(AudioConverter.FORMATS.keys())}")
