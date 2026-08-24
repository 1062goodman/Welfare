import React, { useState } from 'react';
import { View, Text, TextInput, Button, StyleSheet, ActivityIndicator } from 'react-native';

import { sendChatMessage } from '../../api/chatApi'; 

export default function IndexScreen() {
  // 화면에서 상태를 관리하기 위한 변수들 (기억 장치)
  const [inputText, setInputText] = useState<string>(''); // 내가 입력하는 글
  const [replyText, setReplyText] = useState<string>('여기에 챗봇 답변이 표시됩니다.'); // 봇의 답변
  const [isLoading, setIsLoading] = useState<boolean>(false); // 로딩 상태

  // 전송 버튼을 눌렀을 때 실행될 함수
  const handleSend = async () => {
    // 빈칸이면 안 보내기
    if (inputText.trim() === '') return;

    setIsLoading(true);
    setReplyText('서버에서 답변을 가져오는 중입니다... ⏳');

    // API 통신 시도
    // 테스트용이므로 session_id는 임의로 'test-123'을 넣었습니다.
    const response = await sendChatMessage('test-123', inputText);
    
    // 받아온 답변을 화면에 띄우기 위해 변수 업데이트
    setReplyText(response);
    setIsLoading(false);
    setInputText(''); // 입력창 비우기
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>🔌 API 통신 테스트 🔌</Text>

      {/* 챗봇의 답변을 보여주는 영역 */}
      <View style={styles.replyBox}>
        {isLoading ? (
          <ActivityIndicator size="large" color="#0000ff" />
        ) : (
          <Text style={styles.replyText}>{replyText}</Text>
        )}
      </View>

      {/* 글자를 입력하는 영역 */}
      <TextInput
        style={styles.input}
        value={inputText}
        onChangeText={setInputText}
        placeholder="챗봇에게 보낼 메시지를 입력하세요"
      />

      {/* 전송 버튼 */}
      <Button 
        title={isLoading ? "전송 중..." : "서버로 보내기"} 
        onPress={handleSend} 
        disabled={isLoading} 
      />
    </View>
  );
}

// 최소한의 구분을 위한 아주 단순한 스타일
const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 20,
  },
  replyBox: {
    minHeight: 150,
    padding: 15,
    backgroundColor: '#f0f0f0',
    borderRadius: 8,
    marginBottom: 20,
    justifyContent: 'center',
  },
  replyText: {
    fontSize: 16,
    lineHeight: 24,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    padding: 10,
    borderRadius: 8,
    marginBottom: 10,
    fontSize: 16,
  },
});