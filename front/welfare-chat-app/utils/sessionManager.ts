// utils/sessionManager.ts
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';

// 저장소에 저장될 이름표
const SESSION_KEY = '@app_session_id';

/**
 * 폰에서 세션 아이디를 가져옵니다. 
 * 없으면 새로 만들어서 저장한 뒤 가져옵니다.
 */
export const getSessionId = async (): Promise<string> => {
  try {
    // 1. 폰 창고에서 아이디 찾기
    const storedSessionId = await AsyncStorage.getItem(SESSION_KEY);
    
    if (storedSessionId) {
      // 2. 있으면 그대로 반환 (기존 유저)
      return storedSessionId;
    } else {
      // 3. 없으면 새로 UUID 생성 (신규 유저)
      const newSessionId = Crypto.randomUUID();
      
      // 4. 새로 만든 걸 폰 창고에 영구 저장
      await AsyncStorage.setItem(SESSION_KEY, newSessionId);
      return newSessionId;
    }
  } catch (error) {
    console.error("세션 아이디를 가져오는 중 에러 발생:", error);
    // 에러 발생 시 임시 아이디 반환 (앱 멈춤 방지)
    return `temp-${Date.now()}`; 
  }
};