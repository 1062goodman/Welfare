export const FONT_SIZE_PRESETS = {
  small: { message: 13, input: 13, title: 14 },
  medium: { message: 18, input: 17, title: 20 },  
  large: { message: 25, input: 25, title: 25 },
};

export type FontSizeKey = keyof typeof FONT_SIZE_PRESETS;