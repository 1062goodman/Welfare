import React, { useState, useEffect, useRef } from 'react';
import { View, Text, Button, PermissionsAndroid, Platform } from 'react-native';
import LiveAudioStream from 'react-native-live-audio-stream';
import { Buffer } from 'buffer';

export default function AudioSocketTest() {
  const [status, setStatus] = useState('연결 대기 중...');
  const [resultText, setResultText] = useState('');
  const ws = useRef(null);

  useEffect(() => {

     // 마이크 권한 요청 (안드로이드)
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
      });``
      
    }

    setupMic();
    // WebSocket 연결 설정
    const SERVER_URL = 'wss://welfare-1gs5.onrender.com/ws/chat/test_session_1';
    ws.current = new WebSocket(SERVER_URL);

    ws.current.onopen = ( ) => setStatus('소켓 연결 성공');
    ws.current.onclose = () => setStatus('소켓 연결 끊어짐');
    ws.current.onerror = (e) => setStatus(`소켓 에러: ${e.message}`);
    
    // 서버로부터 결과 수신
    ws.current.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.recognized_text) {
        setResultText((prev) => prev + '\n나: ' + data.recognized_text);
        setStatus('변환 완료'); 
      }
    };

   
  

    

    //  오디오 청크 수신 이벤트 (녹음 중 계속 발생)
    LiveAudioStream.on('data', (base64Chunk) => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        // Base64를 순수 바이너리(ArrayBuffer)로 변환하여 전송
        const binaryData = Buffer.from(base64Chunk, 'base64');
        const arraybuffer = binaryData.buffer.slice(binaryData.byteOffset, binaryData.byteOffset + binaryData.byteLength)
        ws.current.send(arraybuffer);
      }
    });

    return () => {
      if (ws.current) ws.current.close();
      LiveAudioStream.stop();
    };
  }, []);

  //  녹음 제어 함수
  const startRecording = () => {
    setStatus('녹음 중... (데이터 전송)');
    LiveAudioStream.start();
  };

  const stopRecording = () => {
    LiveAudioStream.stop();
    if (ws.current) {
      ws.current.send('STOP_RECORDING');
      setStatus('서버 변환 대기 중...');
    }
  };

  return (
    <View style={{ padding: 30, marginTop: 50 }}>
      <Text style={{ fontSize: 18, marginBottom: 20 }}>상태: {status}</Text>
      
      <View style={{ flexDirection: 'row', gap: 10, marginBottom: 20 }}>
        <Button title="녹음 시작" onPress={startRecording} />
        <Button title="녹음 종료 (전송)" onPress={stopRecording} />
      </View>

      <Text style={{ fontSize: 16, fontWeight: 'bold' }}>인식 결과:</Text>
      <Text style={{ marginTop: 10, backgroundColor: '#f0f0f0', padding: 10 }}>
        {resultText}
      </Text>
    </View>
  );
}