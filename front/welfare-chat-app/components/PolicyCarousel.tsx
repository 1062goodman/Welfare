import React, { useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, useWindowDimensions } from 'react-native';
import { PolicyCardData } from '../api/chatApi';
import { useFontSize } from '../contexts/font-size-context';

function Field({ label, value, fs }: { label: string; value?: string | null; fs: number }) {
  if (!value) return null;
  return (
    <View style={{ marginTop: 8 }}>
      <Text style={[s.label, { fontSize: fs - 2 }]}>{label}</Text>
      <Text style={[s.body, { fontSize: fs }]}>{value}</Text>
    </View>
  );
}

function Card({ p, index, total, width }: { p: PolicyCardData; index: number; total: number; width: number }) {
  const { fontSize } = useFontSize();
  const fs = fontSize.message;
  const [open, setOpen] = useState(false);
  const front = p.benefit || p.summary;
  const hasDetail = !!(p.target || p.benefit || p.apply);

  return (
    <View style={[s.card, { width }]}>
      <View style={s.top}>
        <Text style={[s.num, { fontSize: fs - 2 }]}>{index + 1}/{total}</Text>
        {p.is_local && <Text style={[s.badge, { fontSize: fs - 3 }]}>지자체</Text>}
      </View>
      <Text style={[s.name, { fontSize: fs + 2 }]}>{p.name}</Text>
      {!!p.department && <Text style={[s.dept, { fontSize: fs - 2 }]}>{p.department}</Text>}

      {!open && !!front && <Text numberOfLines={3} style={[s.body, { fontSize: fs, marginTop: 8 }]}>{front}</Text>}
      {open && (hasDetail ? (
        <>
          <Field label="지원 대상" value={p.target} fs={fs} />
          <Field label="지원 내용" value={p.benefit} fs={fs} />
          <Field label="신청 방법" value={p.apply} fs={fs} />
        </>
      ) : (
        <Field label="요약" value={p.summary} fs={fs} />
      ))}

      <TouchableOpacity onPress={() => setOpen(!open)} style={{ marginTop: 10 }}>
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
  body: { color: '#5C4632', lineHeight: 22 },
  more: { color: '#E8965A', fontWeight: 'bold' },
});