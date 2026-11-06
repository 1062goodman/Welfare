import React from 'react';
import { Image } from 'react-native';
import { ReplyType } from '../api/chatApi';

const char = require('../assets/mascot/char.png');
const success = require('../assets/mascot/success.png');
const fail = require('../assets/mascot/fail.png');
const no = require('../assets/mascot/no.png');

const BY_TYPE: Record<ReplyType, any> = {
  general: char, ask: char,
  list: success, detail: success,
  no_result: fail, detail_fail: fail, error: fail,
  blocked: no,
};

export default function Mascot({ type, size = 44 }: { type: ReplyType; size?: number }) {
  return <Image source={BY_TYPE[type] ?? char} style={{ width: size, height: size }} resizeMode="contain" />;
}