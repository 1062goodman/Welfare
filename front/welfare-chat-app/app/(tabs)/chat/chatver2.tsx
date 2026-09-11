import React, { useEffect, useState, useRef } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, Platform, PermissionsAndroid } from 'react-native';
import LiveAudioStream from 'react-native-live-audio-stream';
import { Buffer } from 'buffer';

import { get_chat_history, sendChatMessage } from '../../../api/chatApi';
import { getSessionId } from '../../../utils/sessionManager';





export default function ChatScreen() {
  // 기억 장치 세팅 (State)
  const [messages, setMessages] = useState([{ id: '1', text: '안녕하세요! 복지 정책 챗봇입니다.', isUser: false }]);
  const [inputText, setInputText] = useState('');
  const [sessionid, setSessionId] = useState<string>('');
  const [status,  setStatus] = useState('연결 대기 중...');
  const [wsStatus,  setWsStatus] = useState<'connecting' | 'open' | 'closed'>('connecting');


  const ws = useRef<WebSocket|null>(null);
  const SERVER_URL = 'wss://welfare-1gs5.onrender.com/ws/chat/test_session_1';    
  
  const connetWebSocket = () =>{
      setWsStatus('connecting');
      ws.current = new WebSocket(SERVER_URL);

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
      console.log(JSON.stringify(data))
      if (data.recognized_text) setInputText(data.recognized_text);
      console.log("변환된 텍스트:", data.recognized_text);
      };
    };


  //화면이 켜질때 한 번 실행
  useEffect(() => {

    const setupMic = async () => {
          if (Platform.OS === 'android'){
            const granted = await PermissionsAndroid.request(
              PermissionsAndroid.PERMISSIONS.RECORD_AUDIO
            );
            if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
            setStatus('마이크 권한이 필요합니다');
            return;
            }
          }
          // 오디오 스트림 초기 설정 (초당 16000 샘플, 모노)
          LiveAudioStream.init({
            sampleRate: 16000,
            channels: 1,
            bitsPerSample: 16,
            audioSource: 6,
            bufferSize: 4096 
          }as any) ;
          
        }

    setupMic();
    connetWebSocket(); 

    const loadChatroom = async() => {
      try{
        const session = await getSessionId();
        setSessionId(session);

        const history =  await get_chat_history(session); //세션에 맞는 내역 가져옴
        console.log("🚨 새로고침 후 세션 ID 유지되나?:", session);
        setMessages(history);
      }
      catch(error){
        console.error("데이터로드 실패", error);  
      }
    };


    LiveAudioStream.on('data', (base64Chunk) => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        // Base64를 순수 바이너리(ArrayBuffer)로 변환하여 전송
        const binaryData = Buffer.from(base64Chunk, 'base64');
        const arraybuffer = binaryData.buffer.slice(binaryData.byteOffset, binaryData.byteOffset + binaryData.byteLength)
        ws.current.send(arraybuffer);
      }
    });
    
    loadChatroom();

    return () => {
    if (ws.current) ws.current.close();
    LiveAudioStream.stop();
  };
  }, []);
   
  

  const startRecording = () => {
    setStatus('녹음 중... (데이터 전송)');
    LiveAudioStream.start();
    };

  const stopRecording = () => {
    LiveAudioStream.stop();
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send('STOP_RECORDING');
      setStatus('서버 변환 대기 중...');
    } else {
      setStatus('소켓이 연결되어 있지 않습니다.');
    }
    };
  

  

  // 전송 버튼을 눌렀을 때 할 일
  const handleSend = async () => {
    if (inputText.trim() === '') return; // 빈 칸이면 무시

    const newMessage = {
      id: Date.now().toString(), // 임시로 현재 시간을 고유 ID로 사용
      text: inputText,
      isUser: true, // 내가 보낸 메시지라는 표시
    };

    setMessages((prevMessages) => [...prevMessages, newMessage]); // 기존 대화 내역에 새 메시지 추가
    const textToSend = inputText;
    setInputText(''); // 입력창 비우기

    try{
      const botReply = await sendChatMessage(sessionid,textToSend);
      
      const botMessage = {
      id: Date.now().toString(), // 임시로 현재 시간을 고유 ID로 사용
      text: botReply,
      isUser: false, 
      };

      setMessages((prevMessages) => [...prevMessages, botMessage]);

      
    }catch (error) {
      console.error("챗봇 응답 실패:", error);
    }
  };

  // 무한 스크롤 상자 안에서 '말풍선 하나'를 그리는 방법
  const renderBubble = ({ item }: { item: any }) => (
    <View style={[styles.bubble, item.isUser ? styles.myBubble : styles.botBubble]}>
      <Text style={item.isUser ? styles.myText : styles.botText}>{item.text}</Text>
    </View>
  );

  // 화면 그리기 (렌더링)
  return (
    <View style={styles.container}>
      {/* 위쪽: 대화 내역 스크롤 */}
      <FlatList
        data={messages}
        renderItem={renderBubble}
        keyExtractor={(item) => item.id}
        style={styles.chatList}
      />
      {(wsStatus ==='closed') && 
      (<TouchableOpacity style={styles.micButton} onPress={connetWebSocket}>
        <Text style={styles.micButtonText}>🔄 다시 연결</Text>
      </TouchableOpacity>)}
      <Text style={styles.statusText}>{wsStatus}</Text>
      <Text style={styles.statusText}>{status}</Text>
      <View style={styles.voiceArea}>
      <TouchableOpacity style={styles.micButton} onPress={startRecording}>
        <Text style={styles.micButtonText}>🎤 녹음 시작</Text>
      </TouchableOpacity>
      <TouchableOpacity style={[styles.micButton, styles.stopButton]} onPress={stopRecording}>
        <Text style={styles.micButtonText}>■ 녹음 종료</Text>
      </TouchableOpacity>
    </View>

      {/* 아래쪽: 입력창과 전송 버튼 */}
      <View style={styles.inputArea}>
        <TextInput
          style={styles.input}
          value={inputText}
          onChangeText={setInputText} // 글자를 칠 때마다 inputText 기억 장치 업데이트
          placeholder="메시지를 입력하세요..."
        />
        <TouchableOpacity style={styles.sendButton} onPress={handleSend}>
          <Text style={styles.sendButtonText}>전송</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

// 디자인 (Flexbox 스타일링)
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  chatList: { flex: 1, padding: 10 },
  bubble: { maxWidth: '70%', padding: 12, borderRadius: 10, marginVertical: 5 },
  myBubble: { alignSelf: 'flex-end', backgroundColor: '#007AFF' },
  botBubble: { alignSelf: 'flex-start', backgroundColor: '#e5e5ea' },
  myText: { color: 'white', fontSize: 16 },
  botText: { color: 'black', fontSize: 16 },
  inputArea: { flexDirection: 'row', padding: 10, backgroundColor: 'white' },
  input: { flex: 1, borderWidth: 1, borderColor: '#ddd', borderRadius: 20, paddingHorizontal: 15, marginRight: 10 },
  sendButton: { justifyContent: 'center', backgroundColor: '#007AFF', paddingHorizontal: 15, borderRadius: 20 },
  sendButtonText: { color: 'white', fontWeight: 'bold' },
  micButtonText: {color: 'white',fontWeight: 'bold',},
  micButton: {backgroundColor: '#007AFF',paddingVertical: 10, paddingHorizontal: 20, borderRadius: 20,},
  voiceArea: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 10,
    backgroundColor: 'white',
  },
  statusText: {
    textAlign: 'center',
    paddingVertical: 6,
    color: '#666',
    fontSize: 13,
    backgroundColor: '#eee',
  },
   stopButton: {backgroundColor: '#FF3B30',},
});