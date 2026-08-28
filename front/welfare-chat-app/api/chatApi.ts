import axios from 'axios';



// -------------------------------채팅

interface ChatRequest {
  session_id: string;
  user_message: string;
}
interface ChatResponse {
  bot_reply: string;
}

export const sendChatMessage = async (sessionId: string, userMessage: string): Promise<string> => {
    try{
        const requestData: ChatRequest = {
            session_id: sessionId,
            user_message: userMessage
        };

        const response = await axios.post<ChatResponse>("https://welfare-1gs5.onrender.com/chat", requestData);

        return response.data.bot_reply;

    } catch (error) {
        console.error("채팅 API에러", error);
        return "서버 연결 실패."
    }
}


// ---------------------------서버확인

export const helathCheck = async (): Promise<boolean> => {
    try{

        const response = await fetch("https://welfare-1gs5.onrender.com/Health");

        return response.ok;

    } catch (error) {
        console.error("서버 연결 실패",error);
        return false
    }
   
}



// ---------------------------음성인식 파일

export const transcribe = async (): Promise<string> => {
    try{
        

        const response = await axios.get<ChatResponse>("https://welfare-1gs5.onrender.com/transcribe");

        return response.data.bot_reply;

    } catch (error) {
        console.error(error);
        return "서버 연결 실패."
    }
}