'''
This is a tool to parse the infomation of a FLV file.
How to use:
$ python parse_flv.py filename.flv
'''
import os
import os.path
import sys
from collections import OrderedDict
import struct

_tag_count = 0
_offset = 0
_tag_type_dict = {8: 'Audio', 9: 'Video', 18: 'Script'}


def has_next_tag(binary_file_object):
    '''
    Check whether file has next tag.
    Parameter type: file object.
    Return: None
    '''
    if binary_file_object.read(1):
        binary_file_object.seek(-1, 1)
        return True
    return False


def parse_file_header(binary_file_object, output_file_object):
    '''
    Parse the file header.
    Parameter type: file object, file object.
    Return: None
    '''
    output_file_object.write('FLV header' + os.linesep * 2)
    # Parse offset.
    global _offset
    output_file_object.write('## OFFSET' + '\t' + str(_offset) + os.linesep)
    # Parse signature.
    signature = ''
    for i in range(3):
        signature += binary_file_object.read(1)
    output_file_object.write('Signature\t' + signature + os.linesep)
    # Parse version.
    version = ord(binary_file_object.read(1))
    output_file_object.write('Version\t' + str(version) + os.linesep)
    # Parse type flags.
    ascii_type_flags = binary_file_object.read(1)
    # Unpack "ascii type flags" to binary. Binary format: '0b110'
    # Strip starting '0b'. ==>'110'
    # Fill zero to 8 bits. ==>'00000110'
    type_flags = bin(struct.unpack('>b', ascii_type_flags)[0])[2:].zfill(8)
    type_flags_reversed_1 = int(type_flags[0:5])
    output_file_object.write('TypeFlagsReserved' + '\t' + str(type_flags_reversed_1) + os.linesep)
    type_flags_audio = type_flags[5]
    output_file_object.write('TypeFlagsAudio' + '\t' + type_flags_audio + os.linesep)
    type_flags_reversed_2 = type_flags[6]
    output_file_object.write('TypeFlagsReserved' + '\t' + type_flags_reversed_2 + os.linesep)
    type_flags_video = type_flags[7]
    output_file_object.write('TypeFlagsVideo' + '\t' + type_flags_video + os.linesep)
    # Parse data offset.
    data_offset = struct.unpack('>i', binary_file_object.read(4))[0]
    output_file_object.write('DataOffset' + '\t' + str(data_offset) + os.linesep)
    parse_pre_tag_size(binary_file_object, output_file_object)
    _offset += data_offset + 4
    return


def parse_script(binary_file_object, output_file_object):
    '''
    Parse the script tag.
    Parameter type: file object, file object.
    Return: None
    '''
    global _offset
    output_file_object.write('## OFFSET' + '\t' + str(_offset) + os.linesep)
    # Write tag type.
    tag_type_int = struct.unpack('>b', binary_file_object.read(1))[0]
    global _tag_type_dict
    output_file_object.write('TagType' + '\t' + _tag_type_dict[tag_type_int] + os.linesep)
    # Skip the remaining.
    data_size_int = struct.unpack('>i', '\x00' + binary_file_object.read(3))[0]
    binary_file_object.seek(3 + 1 + 3 + data_size_int, 1)
    # Modify _offset.
    _offset += 11 + data_size_int + 4
    return


def parse_audio(binary_file_object, output_file_object):
    '''
    Parse the audio tag.
    Parameter type: file object, file object.
    Return: None
    '''
    audio_dict = {'SoundFormat': {0: 'Linear PCM, platform endian',
                                1: 'ADPCM',
                                2: 'MP3',
                                3: 'Linear PCM, little endian',
                                4: 'Nellymoser 16-kHz mono',
                                5: 'Nellymoser 8-kHz mono',
                                6: 'Nellymoser',
                                7: 'G.711 A-law logarithmic PCM',
                                8: 'G.711 mu-law logarithmic PCM',
                                9: 'reserved',
                                10: 'AAC',
                                11: 'Speex',
                                14: 'MP3 8-Khz',
                                15: 'Device-specific sound}'},
                'SoundRate': {0: '5.5-kHz', 1: '11-kHz', 2: '22-kHz', 3: '44-kHz'},
                'SoundSize': {0: 'snd8Bit', 1: 'snd16Bit'},
                'SoundType': {0: 'sndMono', 1: 'sndStereo'}}
    # The unit of audio data field is bit.
    audio_data_field = OrderedDict([('SoundFormat', 4), ('SoundRate', 2), ('SoundSize', 1), ('SoundType', 1)])
    data_size_int = parse_tag_header(binary_file_object, output_file_object)
    ascii_audio_info = binary_file_object.read(1)
    binary_audio_info = ascii_to_binary(ascii_audio_info)
    accumulation = 0
    for field in audio_data_field:
        new_accumulation = accumulation + audio_data_field[field]
        field_value = int(binary_audio_info[accumulation: new_accumulation], 2)
        output_file_object.write(field + '\t' + audio_dict[field][field_value] + os.linesep)
        accumulation = new_accumulation
    # Skip data area.
    binary_file_object.seek(data_size_int - 1, 1)
    return


def parse_video(binary_file_object, output_file_object):
    '''
    Parse the video tag.
    Parameter type: file object, file object.
    Return: None
    '''
    video_dict = {'FrameType': {1: 'keyframe (for AVC, a seekable frame)',
                                2: 'inter frame (for AVC, a non-seekable frame)',
                                3: 'disposable inter frame (H.263 only)',
                                4: 'generated keyframe (reserved for server use only)',
                                5: 'video info/command frame'},
                'CodecID': {1: 'JPEG (currently unused)',
                            2: 'Sorenson H.263',
                            3: 'Screen video',
                            4: 'On2 VP6',
                            5: 'On2 VP6 with alpha channel',
                            6: 'Screen video version 2',
                            7: 'AVC'}}
    # The unit of video data field is bit.
    video_data_field = OrderedDict([('FrameType', 4), ('CodecID', 4)])
    data_size_int = parse_tag_header(binary_file_object, output_file_object)
    ascii_video_info = binary_file_object.read(1)
    binary_video_info = ascii_to_binary(ascii_video_info)
    accumulation = 0
    for field in video_data_field:
        new_accumulation = accumulation + video_data_field[field]
        field_value = int(binary_video_info[accumulation: new_accumulation], 2)
        output_file_object.write(field + '\t' + video_dict[field][field_value] + os.linesep)
        accumulation = new_accumulation
    binary_file_object.seek(data_size_int - 1, 1)
    return


def ascii_to_binary(ascii_str):
    binary = ''
    for c in ascii_str:
        binary += bin(ord(c))[2:].zfill(8)
    return binary


def parse_tag_header(binary_file_object, output_file_object):
    '''
    Parse the header part of a tag.
    Parameter type: file object, file object.
    Return: integer type data size.
    '''
    tag_type_int = struct.unpack('>b', binary_file_object.read(1))[0]
    data_size_int = struct.unpack('>i', '\x00' + binary_file_object.read(3))[0]
    timestamp_int = struct.unpack('>i', '\x00' + binary_file_object.read(3))[0]
    timestamp_extended = struct.unpack('>b', binary_file_object.read(1))[0]
    stream_id = struct.unpack('>i', '\x00' + binary_file_object.read(3))[0]
    # Write to output file.
    global _offset
    output_file_object.write('## OFFSET' + '\t' + str(_offset) + os.linesep)
    global _tag_type_dict
    output_file_object.write('TagType' + '\t' + _tag_type_dict[tag_type_int] + os.linesep)
    output_file_object.write('DataSize' + '\t' + str(data_size_int) + os.linesep)
    output_file_object.write('Timestamp' + '\t' + str(timestamp_int) + os.linesep)
    output_file_object.write('TimestampExtended' + '\t' + str(timestamp_extended) + os.linesep)
    output_file_object.write('StreamID' + '\t' + str(stream_id) + os.linesep)
    _offset += 11 + data_size_int + 4
    return data_size_int


def parse_pre_tag_size(binary_file_object, output_file_object):
    '''
    Parse "pre tag size" part which is 4 bytes.
    Parameter type: file object, file object.
    Return: None
    '''
    pre_tag_size = struct.unpack('>i', binary_file_object.read(4))[0]
    output_file_object.write('PreviousTagSize' + '\t' + str(pre_tag_size) + os.linesep)
    return


def parse_flv(input_path, output_path):
    '''
    Parse the whole flv file.
    Parameter type: os path object, os path object.
    Return: None
    '''
    binary_file_object = open(input_path, 'rb')
    # Create a new empty output file.
    output_file_object = open(output_path, 'wb')
    output_file_object.close()
    # Append the parsed content.
    output_file_object = open(output_path, 'ab')
    parse_file_header(binary_file_object, output_file_object)
    output_file_object.write(os.linesep * 2)
    global _tag_count
    while (has_next_tag(binary_file_object)):
        _tag_count += 1
        output_file_object.write(os.linesep * 2 + 'Tag No. ' + str(_tag_count) + os.linesep * 2)
        tag_type_int = struct.unpack('>b', binary_file_object.read(1))[0]
        binary_file_object.seek(-1, 1)
        if tag_type_int == 8:
            parse_audio(binary_file_object, output_file_object)
        elif tag_type_int == 9:
            parse_video(binary_file_object, output_file_object)
        else:
            parse_script(binary_file_object, output_file_object)
        parse_pre_tag_size(binary_file_object, output_file_object)
    return


def main():
    input_path = os.path.abspath(sys.argv[1])
    # Wrong file path.
    if not os.path.isfile(input_path):
        print 'File not exit: ' + input_path
        return
    # Output file is created in the same directory as input file.
    dir_path = os.path.dirname(input_path)
    output_path = os.path.join(dir_path, 'output.txt')
    parse_flv(input_path, output_path)
    print 'Succeed!'
    print 'Output file path is ' + output_path
    return


if __name__ == '__main__':
    main()
