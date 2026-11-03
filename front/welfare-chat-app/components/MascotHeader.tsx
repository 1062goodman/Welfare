import React from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';
import { ReplyType } from '../api/chatApi';
import { useFontSize } from '../contexts/font-size-context';



const IMG = {
  char: require('../assets/mascot/char.png'),
  success: require('../assets/mascot/success.png'),
  fail: require('../assets/mascot/fail.png'),
  blocked: require('../assets/mascot/no.png'),
}

const MOOD: Record<ReplyType, {img:keyof typeof IMG; text: string}> = {
  general:     { img: 'char',    text: '무엇이 궁금하세요?' },
  ask:         { img: 'char',    text: '조금만 더 알려 주세요!' },
  list:        { img: 'success', text: '찾았어요! 아래를 확인해 보세요.' },
  detail:      { img: 'success', text: '자세히 정리해 드렸어요.' },
  no_result:   { img: 'fail',    text: '못 찾았어요... 다르게 말해 주실래요?' },
  detail_fail: { img: 'fail',    text: '그 정책은 찾지 못했어요.' },
  error:       { img: 'fail',    text: '서버가 잠깐 쉬고 있어요.' },
  blocked:     { img: 'blocked', text: '그건 도와드릴 수 없어요.' },
}

export default function MascotHeader({ mood }: { mood: ReplyType }) {
  const { fontSize } = useFontSize();
  const m = MOOD[mood] ?? MOOD.general;   // 모르는 값이면 기본

  return (
    <View style={styles.row}>
      <Image source={IMG[m.img]} style={styles.img} resizeMode="contain" />
      <View style={styles.bubble}>
        <Text style={[styles.text, { fontSize: fontSize.message }]}>{m.text}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingBottom: 8, gap: 8 },
  img: { width: 80, height: 80 },
  bubble: { flex: 1, backgroundColor: '#F3E5D8', borderRadius: 14, padding: 12 },
  text: { color: '#5C4632' },
});