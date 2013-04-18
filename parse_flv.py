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
_TAB_SIZE = 20


def ascii_to_binary(ascii_str):
    binary = ''
    for c in ascii_str:
        binary += bin(ord(c))[2:].zfill(8)
    return binary


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
    to_write = []
    to_write.append('FLV header' + os.linesep * 2)
    # Parse offset.
    global _offset
    to_write.append('## OFFSET' + '\t' + str(_offset) + os.linesep)
    # Parse signature.
    signature = ''
    for i in range(3):
        signature += binary_file_object.read(1)
    to_write.append('Signature\t' + signature + os.linesep)
    # Parse version.
    version = ord(binary_file_object.read(1))
    to_write.append('Version\t' + str(version) + os.linesep)
    # Parse type flags.
    ascii_type_flags = binary_file_object.read(1)
    # Unpack "ascii type flags" to binary. Binary format: '0b110'
    # Strip starting '0b'. ==>'110'
    # Fill zero to 8 bits. ==>'00000110'
    type_flags = bin(struct.unpack('>B', ascii_type_flags)[0])[2:].zfill(8)
    type_flags_reversed_1 = int(type_flags[0:5])
    type_flags_audio = type_flags[5]
    type_flags_reversed_2 = type_flags[6]
    type_flags_video = type_flags[7]
    # Parse data offset.
    data_offset = struct.unpack('>I', binary_file_object.read(4))[0]
    to_write += ['TypeFlagsReserved' + '\t' + str(type_flags_reversed_1) + os.linesep,
                'TypeFlagsAudio' + '\t' + type_flags_audio + os.linesep,
                'TypeFlagsReserved' + '\t' + type_flags_reversed_2 + os.linesep,
                'TypeFlagsVideo' + '\t' + type_flags_video + os.linesep,
                'DataOffset' + '\t' + str(data_offset) + os.linesep]
    # Expand tab size to _TAB_SIZE.
    global _TAB_SIZE
    to_write = [s.expandtabs(_TAB_SIZE) for s in to_write]
    output_file_object.writelines(to_write)
    parse_pre_tag_size(binary_file_object, output_file_object)
    _offset += data_offset + 4
    return


def is_ECMA_end(binary_file_object):
    '''
    Judge whether it is the end of a ECMA array.
    Parameter type: file object.
    Return: boolean
    '''
    is_end = False
    value = struct.unpack('>I', '\x00' + binary_file_object.read(3))[0]
    if value == 9:
        is_end = True
    binary_file_object.seek(-3, 1)
    return is_end


def parse_script_data(binary_file_object, output_file_object):
    '''
    Parse the script data value recursively.
    Parameter type: file object, file object.
    Return: None
    '''
    to_write = []
    value_type = struct.unpack('>B', binary_file_object.read(1))[0]
    to_write.append('Type' + '\t' + str(value_type) + os.linesep)
    # Value type is 2.
    string_size = struct.unpack('>H', binary_file_object.read(2))[0]
    string = binary_file_object.read(string_size)
    to_write += ['String Size' + '\t' + str(string_size) + os.linesep,
                'String' + '\t' + string + os.linesep]
    # Value type is 8.
    value_type = struct.unpack('>B', binary_file_object.read(1))[0]
    array_size = struct.unpack('>I', binary_file_object.read(4))[0]
    to_write += ['Type' + '\t' + str(value_type) + os.linesep,
                'ECMA Array Size' + '\t' + str(array_size) + os.linesep]
    ECMA_to_write = []
    while (not is_ECMA_end(binary_file_object)):
        name_size = struct.unpack('>H', binary_file_object.read(2))[0]
        name = binary_file_object.read(name_size)
        ECMA_elem_type = struct.unpack('>B', binary_file_object.read(1))[0]
        if ECMA_elem_type == 0:
            value = struct.unpack('>d', binary_file_object.read(8))[0]
        if ECMA_elem_type == 1:
            value = struct.unpack('>B', binary_file_object.read(1))[0]
        if ECMA_elem_type == 2:
            string_size = struct.unpack('>H', binary_file_object.read(2))[0]
            value = binary_file_object.read(string_size)
        if ECMA_elem_type == 12:
            string_size = struct.unpack('>I', binary_file_object.read(4))[0]
            value = binary_file_object.read(string_size)
        output_file_object.write(name + '\t' + str(value) + os.linesep)
    #     ECMA_to_write.append(name + '\t' + str(value))
    # output_file_object.writelines(ECMA_to_write)
    return


def parse_script(binary_file_object, output_file_object):
    '''
    Parse the script tag.
    Parameter type: file object, file object.
    Return: None
    '''
    parse_tag_header(binary_file_object, output_file_object)
    parse_script_data(binary_file_object, output_file_object)
    return


def parse_tag_header(binary_file_object, output_file_object):
    '''
    Parse the header part of a tag.
    Parameter type: file object, file object.
    Return: integer type data size.
    '''
    tag_type_int = struct.unpack('>B', binary_file_object.read(1))[0]
    data_size_int = struct.unpack('>I', '\x00' + binary_file_object.read(3))[0]
    timestamp_int = struct.unpack('>I', '\x00' + binary_file_object.read(3))[0]
    timestamp_extended = struct.unpack('>B', binary_file_object.read(1))[0]
    stream_id = struct.unpack('>I', '\x00' + binary_file_object.read(3))[0]
    # Write to output file.
    global _offset
    global _tag_type_dict
    to_write = ['## OFFSET' + '\t' + str(_offset) + os.linesep,
                'TagType' + '\t' + _tag_type_dict[tag_type_int] + os.linesep,
                'DataSize' + '\t' + str(data_size_int) + os.linesep,
                'Timestamp' + '\t' + str(timestamp_int) + os.linesep,
                'TimestampExtended' + '\t' + str(timestamp_extended) + os.linesep,
                'StreamID' + '\t' + str(stream_id) + os.linesep * 2]
    global _TAB_SIZE
    to_write = [s.expandtabs(_TAB_SIZE) for s in to_write]
    output_file_object.writelines(to_write)
    _offset += 11 + data_size_int + 4
    return data_size_int


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
    to_write = []
    for field in audio_data_field:
        new_accumulation = accumulation + audio_data_field[field]
        field_value = int(binary_audio_info[accumulation: new_accumulation], 2)
        to_write.append(field + '\t' + audio_dict[field][field_value] + os.linesep)
        accumulation = new_accumulation
    global _TAB_SIZE
    to_write = [s.expandtabs(_TAB_SIZE) for s in to_write]
    output_file_object.writelines(to_write)
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
    to_write = []
    for field in video_data_field:
        new_accumulation = accumulation + video_data_field[field]
        field_value = int(binary_video_info[accumulation: new_accumulation], 2)
        to_write.append(field + '\t' + video_dict[field][field_value] + os.linesep)
        accumulation = new_accumulation
    global _TAB_SIZE
    to_write = [s.expandtabs(_TAB_SIZE) for s in to_write]
    output_file_object.writelines(to_write)
    binary_file_object.seek(data_size_int - 1, 1)
    return


def parse_pre_tag_size(binary_file_object, output_file_object):
    '''
    Parse "pre tag size" part which is 4 bytes.
    Parameter type: file object, file object.
    Return: None
    '''
    global _TAB_SIZE
    pre_tag_size = struct.unpack('>I', binary_file_object.read(4))[0]
    s = 'PreviousTagSize' + '\t' + str(pre_tag_size) + os.linesep
    output_file_object.write(s.expandtabs(_TAB_SIZE))
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
        tag_type_int = struct.unpack('>B', binary_file_object.read(1))[0]
        binary_file_object.seek(-1, 1)
        if tag_type_int == 8:
            parse_audio(binary_file_object, output_file_object)
        elif tag_type_int == 9:
            parse_video(binary_file_object, output_file_object)
        else:
            parse_script(binary_file_object, output_file_object)
        parse_pre_tag_size(binary_file_object, output_file_object)
    output_file_object.close()
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
