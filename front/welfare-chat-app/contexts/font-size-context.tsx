import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { FONT_SIZE_PRESETS, FontSizeKey } from '@/constants/typographyOption';


const STORAGE_KEY = 'fontSizePreference';

type FontSizeContextType = {
  fontSize: typeof FONT_SIZE_PRESETS[FontSizeKey];
  fontSizeKey: FontSizeKey;
  updateFontSize: (key: FontSizeKey) => void;
};

const FontSizeContext = createContext<FontSizeContextType | undefined>(undefined);

export function FontSizeProvider({children}: {children: React.ReactNode}){
    const [fontSizeKey, setFontSizeKey] = useState<FontSizeKey>('medium');

    useEffect(() => {
        AsyncStorage.getItem(STORAGE_KEY).then((saved) =>{
            if (saved && saved in FONT_SIZE_PRESETS) {
                setFontSizeKey(saved as FontSizeKey);
            }
        });
    }, []);

    const updateFontSize = async (key: FontSizeKey) =>{
        setFontSizeKey(key);
        await AsyncStorage.setItem(STORAGE_KEY, key);
    };

    const value = {
        fontSize: FONT_SIZE_PRESETS[fontSizeKey],
        fontSizeKey,
        updateFontSize,
    };

    return (
        <FontSizeContext.Provider value = {value}>
            {children}
        </FontSizeContext.Provider>
    );

}

export function useFontSize() {
  const context = useContext(FontSizeContext);
  if (context === undefined) {
    throw new Error('useFontSize는 FontSizeProvider 안에서만 쓸 수 있습니다');
  }
  return context;
}

