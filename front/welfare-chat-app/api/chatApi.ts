import axios from 'axios';


// -------------------------------채팅 내역 가져오기

export interface HistoryResponse{
    id:string ,
    text:string ,
    isUser: boolean
}

export const get_chat_history= async (sessionid: string): Promise<HistoryResponse[]> =>{
    try{
        const response = await axios.get<HistoryResponse[]>
        (`https://welfare-1gs5.onrender.com/chat/history/${sessionid}`)

        return response.data;

    }catch (error){
        console.error("대화 내역 불러오기 실패", error);
        return [];

    }

   
}


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

export const healthCheck = async (): Promise<boolean> => {
    try{

        const response = await fetch("https://welfare-1gs5.onrender.com/Health");

        return response.ok;

    } catch (error) {
        console.error("서버 연결 실패",error);
        return false
    }
   
}



// ---------------------------음성인식 파일

export interface AudioFile {
    uri: string;
    name: string;
    type: string;
}

export const transcribe = async (audioData: AudioFile): Promise<string> => {
    try{
        const formData = new FormData();
        
        formData.append('audio_file', {
            uri: audioData.uri,
            name: audioData.name,
            type: audioData.type,
        }as any);
        
        const response = await axios.post("https://welfare-1gs5.onrender.com/transcribe",formData,{
            headers: {
                'Content-Type': 'multipart/form-data',

            }
        });

        return response.data.recognized_text;

    } catch (error) {
        console.error(error);
        return "서버 연결 실패."
    }
}