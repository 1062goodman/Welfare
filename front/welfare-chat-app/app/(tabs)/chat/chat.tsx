import React, { useEffect, useState, useRef } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, Platform, PermissionsAndroid } from 'react-native';
import LiveAudioStream from 'react-native-live-audio-stream';
import { Buffer } from 'buffer';

import { get_chat_history, sendChatMessage } from '../../../api/chatApi';
import { getSessionId } from '../../../utils/sessionManager';
import { useFontSize } from '../../../contexts/font-size-context';

export default function ChatScreen() {
  const [messages, setMessages] = useState([{ id: '1', text: '안녕하세요! 복지 정책 챗봇입니다.', isUser: false }]);
  const [inputText, setInputText] = useState('');
  const [sessionid, setSessionId] = useState<string>('');
  const [status, setStatus] = useState('연결 대기 중...');
  const [wsStatus, setWsStatus] = useState<'connecting..' | 'open' | 'closed'>('connecting..');
  const [isRecording, setIsRecording] = useState(false); //  토글용 state 추가

   const {fontSize} = useFontSize(); //글자크기등 세팅 가져오기
  const ws = useRef<WebSocket | null>(null);
  const SERVER_URL = 'wss://welfare-1gs5.onrender.com/ws/chat/test_session_1';

  const connectWebSocket = () => {
    setWsStatus('connecting..');
    ws.current = new WebSocket(SERVER_URL);

    if (!ws.current) return;

    ws.current.onopen = () => {
      setStatus('소켓 연결 성공');
      setWsStatus('open');
    };
    ws.current.onclose = () => {
      setStatus('소켓 연결 끊어짐');
      setWsStatus('closed');
    };
    ws.current.onerror = (e) => {
      setStatus(`소켓 에러: ${(e as any).message}`);
      setWsStatus('closed');
    };
    ws.current.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.recognized_text) setInputText(data.recognized_text);
    };
  };

  useEffect(() => {
    //마이크 권한
    const setupMic = async () => {
      if (Platform.OS === 'android') {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.RECORD_AUDIO
        );
        if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
          setStatus('마이크 권한이 필요합니다');
          return;
        }
      }
      LiveAudioStream.init({
        sampleRate: 16000,
        channels: 1,
        bitsPerSample: 16,
        audioSource: 6,
        bufferSize: 4096,
      } as any);
    };

    setupMic();
    connectWebSocket();

    //채팅 불러오기
    const loadChatroom = async () => {
      try {
        const session = await getSessionId();
        setSessionId(session);
        const history = await get_chat_history(session);
        setMessages(history);
      } catch (error) {
        console.error('데이터로드 실패', error);
      }
    };

    LiveAudioStream.on('data', (base64Chunk) => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        const binaryData = Buffer.from(base64Chunk, 'base64');
        const arraybuffer = binaryData.buffer.slice(binaryData.byteOffset, binaryData.byteOffset + binaryData.byteLength);
        ws.current.send(arraybuffer);
      }
    });

    loadChatroom();

    return () => {
      if (ws.current) ws.current.close();
      LiveAudioStream.stop();
    };
  }, []);

  // ✅ 시작/종료를 하나로 합친 토글 함수
  const toggleRecording = () => {
    if (isRecording) {
      LiveAudioStream.stop();
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send('STOP_RECORDING');
        setStatus('서버 변환 대기 중...');
      } else {
        setStatus('소켓이 연결되어 있지 않습니다.');
      }
    } else {
      setStatus('녹음 중... ');
      LiveAudioStream.start();
    }
    setIsRecording(!isRecording);
  };

  const handleSend = async () => {
    if (inputText.trim() === '') return;

    const newMessage = { id: Date.now().toString(), text: inputText, isUser: true };
    setMessages((prev) => [...prev, newMessage]);
    const textToSend = inputText;
    setInputText('');

    try {
      const botReply = await sendChatMessage(sessionid, textToSend);
      const botMessage = { id: Date.now().toString(), text: botReply, isUser: false };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error('챗봇 응답 실패:', error);
    }
  };

  const renderBubble = ({ item }: { item: any }) => (
    <View style={[styles.bubble, item.isUser ? styles.myBubble : styles.botBubble]}>
        <Text style={[item.isUser ? styles.myText : styles.botText, {fontSize: fontSize.message}]}>{item.text}</Text>
    </View>
  );
  
  //예시 질문. 나중에 수정
  const SUGGESTED_QUERIES = [
  '기초연금 신청 방법이 궁금해요',
  '장애인 지원금 종류가 뭐가 있나요',
  '청년 주거 지원 알려주세요',
  '난방비 지원은 어떻게 받나요',
  ];


  return (
    <View style={styles.container}>
      {/* ✅ 상단 바: 설정 / 제목 / 메인으로 */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => {}}>
          <Text style={styles.headerIcon}>⚙️</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>대화창</Text>
        <TouchableOpacity onPress={() => {}}>
          <Text style={styles.headerIcon}>🏠</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={messages}
        renderItem={renderBubble}
        keyExtractor={(item) => item.id}
        style={styles.chatList}
      />

      {messages.length === 1 && (
  <View style={styles.suggestionArea}>
    {SUGGESTED_QUERIES.map((query, idx) => (
      <TouchableOpacity
        key={idx}
        style={styles.suggestionChip}
        onPress={() => {
          setInputText(query);
        }}>
        <Text style={styles.suggestionText}>{query}</Text>
      </TouchableOpacity>
    ))}
  </View>
      )}

      {wsStatus === 'closed' && (
        <TouchableOpacity style={styles.reconnectButton} onPress={connectWebSocket}>
          <Text style={styles.reconnectText}>🔄 다시 연결</Text>
        </TouchableOpacity>
      )}
      <Text style={styles.statusText}>{status}</Text>

      {/* ✅ 원형 토글 마이크 버튼 (가운데) */}
      <View style={styles.micArea}>
        <TouchableOpacity
          style={[styles.micCircle, isRecording && styles.micCircleActive]}
          onPress={toggleRecording}
        >
          <Text style={styles.micIcon}>{isRecording ? '■' : '🎤'}</Text>
        </TouchableOpacity>
      </View>

      {/* ✅ 하단 입력줄: + 아이콘 포함 알약 입력창 + 오렌지 전송 버튼 */}
      <View style={styles.inputArea}>
        <View style={styles.inputPill}>
          <Text style={styles.plusIcon}>+</Text>
          <TextInput
            style={styles.input}
            value={inputText}
            onChangeText={setInputText}
            placeholder="메시지 입력창"
            placeholderTextColor="#B0A08C"
          />
        </View>
        <TouchableOpacity style={styles.sendButton} onPress={handleSend}>
          <Text style={styles.sendIcon}>➤</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const CREAM_BG = '#FBF3E7';
const CARD_BG = '#FFFFFF';
const ACCENT_ORANGE = '#E8965A';
const TEXT_DARK = '#5C4632';
const BUBBLE_BOT = '#F3E5D8';

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CREAM_BG },

  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
    backgroundColor: CREAM_BG,
  },
  headerIcon: { fontSize: 20 },
  headerTitle: { fontSize: 16, fontWeight: 'bold', color: TEXT_DARK },

  chatList: { flex: 1, paddingHorizontal: 14 },
  bubble: { maxWidth: '70%', padding: 12, borderRadius: 14, marginVertical: 5 },
  myBubble: { alignSelf: 'flex-end', backgroundColor: ACCENT_ORANGE },
  botBubble: { alignSelf: 'flex-start', backgroundColor: BUBBLE_BOT },
  myText: { color: 'white', fontSize: 15 },
  botText: { color: TEXT_DARK, fontSize: 15 },

  statusText: {
    textAlign: 'center',
    paddingVertical: 4,
    color: '#A08A6F',
    fontSize: 12,
  },
  reconnectButton: {
    alignSelf: 'center',
    backgroundColor: ACCENT_ORANGE,
    paddingVertical: 6,
    paddingHorizontal: 16,
    borderRadius: 16,
    marginTop: 4,
  },
  reconnectText: { color: 'white', fontWeight: 'bold', fontSize: 12 },

  micArea: {
    alignItems: 'center',
    paddingVertical: 16,
  },
  micCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: ACCENT_ORANGE,
    justifyContent: 'center',
    alignItems: 'center',
  },
  micCircleActive: {
    backgroundColor: '#D9502E', // 녹음 중일 때 조금 더 진한 색
  },
  micIcon: { fontSize: 26, color: 'white' },

  inputArea: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingBottom: 16,
    paddingTop: 4,
    gap: 8,
    backgroundColor: CREAM_BG,
  },
  inputPill: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: CARD_BG,
    borderRadius: 24,
    paddingHorizontal: 14,
    paddingVertical: 10,
    gap: 8,
  },
  plusIcon: { fontSize: 18, color: '#B0A08C' },
  input: { flex: 1, fontSize: 14, color: TEXT_DARK },

  sendButton: {
    backgroundColor: ACCENT_ORANGE,
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendIcon: { color: 'white', fontSize: 18 },

  suggestionArea: {
  flexDirection: 'row',
  flexWrap: 'wrap',
  gap: 8,
  paddingHorizontal: 14,
  paddingVertical: 8,
},
suggestionChip: {
  backgroundColor: '#F3E5D8',
  paddingVertical: 8,
  paddingHorizontal: 14,
  borderRadius: 16,
},
suggestionText: {
  color: '#5C4632',
  fontSize: 13,
},


});