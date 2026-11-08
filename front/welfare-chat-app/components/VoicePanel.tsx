import React, { useRef } from 'react';
import { View, Text, TouchableOpacity, Animated, ScrollView, StyleSheet } from 'react-native';
import Mascot from './mascot';
import { useFontSize } from '../contexts/font-size-context';

type Props = {
  state: 'listening' | 'finishing';
  text: string;
  level: Animated.Value;     // 0~1 음량
  noSound: boolean;
  onStop: () => void;
};

const ORANGE = '#E8965A';
const RINGS = [0, 1, 2];

export default function VoicePanel({ state, text, level, noSound, onStop }: Props) {
  const { fontSize } = useFontSize();
  const scrollRef = useRef<ScrollView>(null);
  const finishing = state === 'finishing';
  const lh = Math.round(fontSize.message * 1.45);

  const placeholder = finishing
    ? '정리하고 있어요…'
    : noSound
    ? '소리가 잘 안 들려요. 조금 더 가까이서 말씀해 주세요'
    : '말씀해 주세요';

  return (
    <View style={s.panel}>
      <View style={s.row}>
        <Mascot type="listening" size={96} />
        <View style={[s.caption, { maxHeight: lh * 3 + 24 }]}>
          <ScrollView
            ref={scrollRef}
            onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: false })}
          >
            <Text style={[text ? s.text : s.placeholder, { fontSize: fontSize.message, lineHeight: lh }]}>
              {text || placeholder}
            </Text>
          </ScrollView>
        </View>
      </View>

      <View style={s.waveBox}>
        {RINGS.map((i) => (
          <Animated.View
            key={i}
            pointerEvents="none"
            style={[
              s.ring,
              {
                opacity: level.interpolate({ inputRange: [0, 1], outputRange: [0.12, 0.3 - i * 0.07] }),
                transform: [{
                  scale: level.interpolate({ inputRange: [0, 1], outputRange: [1 + 0.1 * i, 1.4 + 0.25 * i] }),
                }],
              },
            ]}
          />
        ))}
        <TouchableOpacity style={s.stopBtn} onPress={onStop} disabled={finishing}>
          <Text style={s.stopIcon}>{finishing ? '…' : '■'}</Text>
        </TouchableOpacity>
      </View>

      <Text style={[s.label, { fontSize: fontSize.message - 2 }]}>
        {finishing ? ' ' : '다 말씀하셨으면 ■를 눌러 주세요'}
      </Text>
    </View>
  );
}

const s = StyleSheet.create({
  panel: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderTopWidth: 1,
    borderColor: '#F0DFCB',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 16,
    elevation: 8,
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  caption: { flex: 1, backgroundColor: '#FBF3E7', borderRadius: 16, padding: 12 },
  text: { color: '#5C4632' },
  placeholder: { color: '#B0A08C' },
  waveBox: { height: 120, alignItems: 'center', justifyContent: 'center' },
  ring: { position: 'absolute', width: 72, height: 72, borderRadius: 36, backgroundColor: ORANGE },
  stopBtn: {
    width: 72, height: 72, borderRadius: 36,
    backgroundColor: '#D9502E', justifyContent: 'center', alignItems: 'center',
  },
  stopIcon: { fontSize: 28, color: 'white' },
  label: { textAlign: 'center', color: '#A08A6F' },
});