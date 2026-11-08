import React, { useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, useWindowDimensions, Linking } from 'react-native';
import { PolicyCardData } from '../api/chatApi';
import { useFontSize } from '../contexts/font-size-context';

function Field({ label, value, fs, lines }: { label: string; value?: string | null; fs: number; lines?: number }) {
  if (!value) return null;
  return (
    <View style={{ marginTop: 10 }}>
      <Text style={[s.label, { fontSize: fs - 3 }]}>{label}</Text>
      <Text numberOfLines={lines} style={[s.body, { fontSize: fs - 1, lineHeight: Math.round((fs - 1) * 1.45) }]}>
        {value}
      </Text>
    </View>
  );
}

function Card({ p, index, total, width }: { p: PolicyCardData; index: number; total: number; width: number }) {
  const { fontSize } = useFontSize();
  const fs = fontSize.message;
  const [open, setOpen] = useState(false);

  return (
    <View style={[s.card, { width }]}>
      <View style={s.top}>
        <Text style={[s.num, { fontSize: fs - 3 }]}>{index + 1}/{total}</Text>
        {p.is_local && <Text style={[s.badge, { fontSize: fs - 4 }]}>지자체</Text>}
      </View>
      <Text style={[s.name, { fontSize: fs + 1, lineHeight: Math.round((fs + 1) * 1.35) }]}>{p.name}</Text>
      {!!p.department && <Text style={[s.dept, { fontSize: fs - 3 }]}>{p.department}</Text>}

      <Field label="요약" value={p.summary} fs={fs} lines={open ? undefined : 3} />
      <Field label="지원 대상" value={p.target} fs={fs} lines={open ? undefined : 2} />

      {open && (
        <>
          <Field label="지원 내용" value={p.benefit} fs={fs} />
          <Field label="신청 방법" value={p.apply} fs={fs} />
          {!!p.url && (
            <TouchableOpacity style={s.linkBtn} onPress={() => Linking.openURL(p.url!)}>
              <Text style={[s.linkText, { fontSize: fs - 1 }]}>복지로에서 자세히 보기 ›</Text>
            </TouchableOpacity>
          )}
        </>
      )}

      <TouchableOpacity onPress={() => setOpen(!open)} style={{ marginTop: 12 }}>
        <Text style={[s.more, { fontSize: fs - 1 }]}>{open ? '접기' : '더보기'}</Text>
      </TouchableOpacity>
    </View>
  );
}

export default function PolicyCarousel({ policies }: { policies: PolicyCardData[] }) {
  const { width } = useWindowDimensions();
  const cardW = width * 0.78;
  const gap = 10;
  return (
    <FlatList
      horizontal
      data={policies}
      keyExtractor={(p) => p.id}
      showsHorizontalScrollIndicator={false}
      snapToInterval={cardW + gap}
      decelerationRate="fast"
      ItemSeparatorComponent={() => <View style={{ width: gap }} />}
      contentContainerStyle={{ paddingRight: 14 }}
      style={{ marginTop: 4, marginBottom: 8 }}
      renderItem={({ item, index }) => <Card p={item} index={index} total={policies.length} width={cardW} />}
    />
  );
}

const s = StyleSheet.create({
  card: { backgroundColor: '#FFFFFF', borderRadius: 16, padding: 14, borderWidth: 1, borderColor: '#F0DFCB' },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  num: { color: '#E8965A', fontWeight: 'bold' },
  badge: { color: '#5C4632', backgroundColor: '#F3E5D8', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8 },
  name: { color: '#5C4632', fontWeight: 'bold', marginTop: 6 },
  dept: { color: '#A08A6F', marginTop: 2 },
  label: { color: '#A08A6F', fontWeight: 'bold' },
  body: { color: '#5C4632'},
  more: { color: '#E8965A', fontWeight: 'bold' },
  linkBtn: { marginTop: 14, backgroundColor: '#FBF3E7', borderRadius: 12, paddingVertical: 12, alignItems: 'center' },
  linkText: { color: '#E8965A', fontWeight: 'bold' },
});