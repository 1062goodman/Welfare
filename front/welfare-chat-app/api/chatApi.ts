import axios from 'axios';

const SERVER_URL = 'https://welfare-1gs5.onrender.com/chat';

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

        const response = await axios.post<ChatResponse>(SERVER_URL, requestData);

        return response.data.bot_reply;

    } catch (error) {
        console.error("채팅 API에러", error);
        return "서버 연결 실패."
    }
}