import { View, Text, TouchableOpacity } from 'react-native';

import { useFontSize } from '@/contexts/font-size-context';

export default function SettingsScreen() {
  const { fontSizeKey, updateFontSize } = useFontSize();

  return (
    

    <View>
      <View>
        <Text>설정창</Text>
        <Text>입니다</Text>
      </View>
      {(['small', 'medium', 'large'] as const).map((key) => (
        <TouchableOpacity key={key} onPress={() => updateFontSize(key)}>
          <Text style={{ fontWeight: fontSizeKey === key ? 'bold' : 'normal' }}>
            {key === 'small' ? '작게' : key === 'medium' ? '보통' : '크게'}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}