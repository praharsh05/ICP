interface TTSRequest {
  text_input: string;
  text_filtering?: string;
  character_voice_gen?: string;
  narrator_enabled?: boolean;
  narrator_voice_gen?: string;
  text_not_inside?: string;
  language?: string;
  output_file_name?: string;
  output_file_timestamp?: boolean;
  autoplay?: boolean;
  autoplay_volume?: number;
}

interface TTSResponse {
  success: boolean;
  audio_file_path?: string;
  audio_file_url?: string;
  error?: string;
}

export class AudioService {
  private static readonly TTS_API_URL = 'http://localhost:7851/api/tts-generate';

  static async generateSpeech(
    text: string,
    options: Partial<TTSRequest> = {}
  ): Promise<TTSResponse> {
    const defaultOptions: TTSRequest = {
      text_input: text,
      text_filtering: "standard",
      character_voice_gen: "male_01.wav",
      narrator_enabled: false,
      narrator_voice_gen: "male_01.wav",
      text_not_inside: "character",
      language: "en",
      output_file_name: "output",
      output_file_timestamp: true,
      autoplay: false,
      autoplay_volume: 0.8,
      ...options
    };

    try {
      const formData = new FormData();
      Object.entries(defaultOptions).forEach(([key, value]) => {
        formData.append(key, String(value));
      });

      const response = await fetch(this.TTS_API_URL, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`TTS API error: ${response.status}`);
      }

      const result = await response.json();
      return result;
    } catch (error) {
      console.error('Text-to-speech error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  }

  static async generateAudioOverview(
    documents: string[],
    voice: string = "male_01.wav"
  ): Promise<TTSResponse> {
    const overviewText = this.createOverviewScript(documents);
    return this.generateSpeech(overviewText, {
      character_voice_gen: voice,
      narrator_voice_gen: voice,
      output_file_name: "audio_overview"
    });
  }

  private static createOverviewScript(documents: string[]): string {
    const docCount = documents.length;
    const introduction = `Welcome to your ICP GPT Audio Overview. I'll be walking you through the key insights from your ${docCount} document${docCount > 1 ? 's' : ''}.`;

    let script = introduction + " ";

    documents.forEach((doc, index) => {
      const summary = this.extractKeySummary(doc);
      script += `Document ${index + 1}: ${summary} `;
    });

    script += "This concludes your audio overview. You can ask me any questions about these documents in the chat.";

    return script;
  }

  private static extractKeySummary(document: string): string {
    // Simple extraction - first 200 characters or first paragraph
    const firstParagraph = document.split('\n\n')[0];
    return firstParagraph.length > 200
      ? firstParagraph.substring(0, 200) + "..."
      : firstParagraph;
  }

  static getAvailableVoices(): string[] {
    return [
      "male_01.wav",
      "female_01.wav",
      "male_02.wav",
      "female_02.wav"
    ];
  }
}