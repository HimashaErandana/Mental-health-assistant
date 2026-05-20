import { useState, useRef } from 'react'

const API_URL = 'http://localhost:8000/chat/'
const TTS_API = 'http://localhost:8000/tts/speak/stream'

function ChatUI() {
  const [isOpen, setIsOpen] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [messages, setMessages] = useState([
    { id: 1, text: "Hello! How can I help you today?", isUser: false },
  ])
  
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const audioRef = useRef(null)

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        await sendAudioToAPI(audioBlob)
        
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
      setIsOpen(true)
    } catch (error) {
      console.error('Error starting recording:', error)
      alert('Could not access microphone. Please check permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setIsProcessing(true)
    }
  }

  const toggleRecording = () => {
    // Stop any playing audio when toggling
    if (isPlaying) {
      stopSpeaking()
      return
    }
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const closeChat = () => {
    if (isRecording) {
      stopRecording()
    }
    stopSpeaking()
    setIsOpen(false)
    setIsRecording(false)
    setIsProcessing(false)
  }

  const speakText = async (text) => {
    // Stop any previous audio
    stopSpeaking()
    setIsPlaying(true)
    
    // Clean the text - remove asterisks and markdown formatting
    const cleanedText = text
      .replace(/\* /g, '- ')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/#+\s*/g, '')
      .replace(/```[\s\S]*?```/g, '')
      .trim()
    
    try {
      const response = await fetch(TTS_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: cleanedText })
      })
      
      if (!response.ok) {
        throw new Error('TTS failed')
      }
      
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      
      if (audioRef.current) {
        audioRef.current.pause()
        URL.revokeObjectURL(audioRef.current.src)
      }
      
      audioRef.current = new Audio(url)
      audioRef.current.onended = () => setIsPlaying(false)
      audioRef.current.onerror = () => setIsPlaying(false)
      audioRef.current.play()
      
    } catch (error) {
      console.error('TTS error:', error)
      setIsPlaying(false)
    }
  }

  const stopSpeaking = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
    setIsPlaying(false)
  }

  const sendAudioToAPI = async (audioBlob) => {
    console.log('Sending audio to backend:', audioBlob)
    try {
      const formData = new FormData()
      formData.append('file', audioBlob, 'audio.webm')

      const response = await fetch(API_URL, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('API request failed')
      }

      const data = await response.json()

      if (data.transcribed_text) {
        const userMessage = {
          id: Date.now(),
          text: data.transcribed_text,
          isUser: true
        }
        setMessages(prev => [...prev, userMessage])
      }

      if (data.response) {
        const responseText = typeof data.response === 'string' 
          ? data.response 
          : data.response.result || data.response.answer || JSON.stringify(data.response)
        
        const aiMessage = {
          id: Date.now() + 1,
          text: responseText,
          isUser: false
        }
        setMessages(prev => [...prev, aiMessage])
        
        // Auto-play the response with TTS
        speakText(responseText)
      }

    } catch (error) {
      console.error('Error sending audio:', error)
      const errorMessage = {
        id: Date.now(),
        text: 'Sorry, I encountered an error. Please try again.',
        isUser: false
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsProcessing(false)
    }
  }

  const renderMessageText = (text) => {
    const lines = text.split('\n')
    return lines.map((line, lineIdx) => {
      const trimmed = line.trim()
      
      // Bullet list item: "* Item" or "- Item"
      if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
        const content = trimmed.replace(/^[\*\-]\s*/, '')
        return (
          <div key={lineIdx} className="flex items-start gap-2 ml-2">
            <span className="text-pink-400 mt-1">•</span>
            <span>{renderFormattedContent(content)}</span>
          </div>
        )
      }
      
      // Numbered list: "1. Item" or "1) Item"
      if (/^\d+[.)]\s/.test(trimmed)) {
        const match = trimmed.match(/^(\d+)[.)]\s*(.*)$/)
        if (match) {
          return (
            <div key={lineIdx} className="flex items-start gap-2 ml-2">
              <span className="text-blue-400 font-medium min-w-[20px]">{match[1]}.</span>
              <span>{renderFormattedContent(match[2])}</span>
            </div>
          )
        }
      }
      
      // Section header: "SOME TEXT:" (all caps followed by colon)
      if (/^[A-Z][A-Z\s]+:$/.test(trimmed) && trimmed.length > 3) {
        return (
          <div key={lineIdx} className="font-bold text-pink-400 mt-3 mb-1 uppercase text-sm">
            {trimmed}
          </div>
        )
      }
      
      // Empty line
      if (trimmed === '') {
        return <div key={lineIdx} className="h-2" />
      }
      
      // Regular paragraph
      return (
        <p key={lineIdx} className="leading-relaxed">
          {renderFormattedContent(trimmed)}
        </p>
      )
    })
  }

  const renderFormattedContent = (text) => {
    if (!text) return null
    
    // Bold: **text**
    const parts = text.split(/(\*\*[^*]+\*\*)/)
    return parts.map((part, idx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={idx} className="font-bold text-white">{part.slice(2, -2)}</strong>
      }
      
      // Italic: *text* (but not **)
      const italicParts = part.split(/(\*[^*]+\*)/)
      return italicParts.map((ip, iidx) => {
        if (ip.startsWith('*') && ip.endsWith('*') && !ip.startsWith('**')) {
          return <em key={`${idx}-${iidx}`} className="text-pink-300">{ip.slice(1, -1)}</em>
        }
        return ip
      })
    })
  }

  return (
    <div className="relative w-full h-screen bg-gray-900 flex items-center justify-center overflow-hidden">
      <label 
        onClick={toggleRecording}
        className={`orb fixed left-1/2 w-16 h-16 flex cursor-pointer transition-all duration-500 cubic-bezier(0.175, 0.885, 0.32, 1.275) z-[999999] ${isRecording ? 'recording' : ''} ${isPlaying ? 'playing' : ''}`}
        style={{
          top: isOpen ? 'auto' : '50%',
          bottom: isOpen ? '20px' : 'auto',
          transform: isOpen ? 'translateX(-50%)' : 'translate(-50%, -50%)',
          filter: isRecording
            ? 'drop-shadow(0 0 20px rgba(236, 72, 153, 0.8)) drop-shadow(0 0 10px rgba(59, 130, 246, 0.8))'
            : isPlaying
              ? 'drop-shadow(0 0 25px rgba(59, 130, 246, 1)) drop-shadow(0 0 15px rgba(59, 130, 246, 0.8))'
              : isOpen 
                ? 'drop-shadow(0 0 12px rgba(59, 130, 246, 0.3)) drop-shadow(0 0 5px rgba(236, 72, 153, 0.3))'
                : 'drop-shadow(0 0 4px rgba(255, 255, 255)) drop-shadow(0 0 12px rgba(255, 255, 255)) drop-shadow(0 0 12px rgba(59, 130, 246, 0.3)) drop-shadow(0 0 5px rgba(236, 72, 153, 0.3))'
        }}
      >
        <div className="icons absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white flex flex-col transition-all duration-300 ease-in-out z-[999]">
          {/* Mic icon - shown when not recording and not playing */}
          <svg id="mic-icon" className={`svg w-6 h-6 flex-shrink-0 transition-all duration-300 ease-in-out ${isOpen ? 'opacity-100 drop-shadow(0 0 4px #ffffff)' : 'opacity-50'} ${isRecording || isPlaying ? 'hidden' : ''}`} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <g fill="none" className="mic">
              <rect width="8" height="13" x="8" y="2" fill="currentColor" rx="4"></rect>
              <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 11a7 7 0 1 0 14 0m-7 10v-2"></path>
            </g>
          </svg>
          
          {/* Stop (X) icon - shown when recording */}
          <svg id="stop-icon" className={`w-6 h-6 flex-shrink-0 ${isRecording ? 'block' : 'hidden'}`} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <g fill="currentColor">
              <path d="M18.3 5.71a.996.996 0 0 0-1.41 0L12 10.59L7.11 5.7A.996.996 0 1 0 5.7 7.11L10.59 12L5.7 16.89a.996.996 0 1 0 1.41 1.41L12 13.41l4.89 4.89a.996.996 0 1 0 1.41-1.41L13.41 12l4.89-4.89c.38-.38.38-1.02 0-1.4"></path>
            </g>
          </svg>
          
          {/* Volume/Sound icon - shown when playing */}
          <svg id="playing-icon" className={`w-6 h-6 flex-shrink-0 text-blue-400 animate-pulse ${isPlaying && !isRecording ? 'block' : 'hidden'}`} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <g fill="currentColor">
              <path d="M3 9v6h4l5 5V4L7 9H3z"/>
              <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
              <path d="M14 3.23v2.06c2.83.48 5 2.94 5 5.71s-2.17 5.23-5 5.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
            </g>
          </svg>
        </div>
        
        <div 
          className="ball w-16 h-16 rounded-full"
          style={{
            background: isRecording 
              ? 'linear-gradient(135deg, #ef4444, #f97316)' 
              : isPlaying
                ? 'linear-gradient(135deg, #3b82f6, #8b5cf6)'
                : 'linear-gradient(135deg, #ec4899, #3b82f6)',
            filter: 'url(#gooey)',
            animation: isRecording 
              ? 'pulse 0.5s ease-in-out infinite' 
              : isPlaying
                ? 'wave 0.8s ease-in-out infinite'
                : !isOpen
                  ? 'pulse 2s ease-in-out infinite'
                  : 'none'
          }}
        />
        
        <svg style={{ pointerEvents: 'none' }} className="absolute">
          <filter id="gooey">
            <feGaussianBlur in="SourceGraphic" stdDeviation="6"></feGaussianBlur>
            <feColorMatrix values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 20 -10"></feColorMatrix>
          </filter>
        </svg>
      </label>
      
      <div 
        className={`container-chat-ia fixed left-1/2 flex flex-col p-4 md:p-6 rounded-[2rem] shadow-lg gap-3 md:gap-4 transition-all duration-600 cubic-bezier(0.175, 0.885, 0.32, 1.1) ${isOpen ? 'opacity-100 blur-0' : 'opacity-0 blur-[50px]'}`}
        style={{
          width: isOpen ? '80vw' : '64px',
          height: isOpen ? '80vh' : '64px',
          maxWidth: isOpen ? '900px' : '64px',
          maxHeight: isOpen ? '700px' : '64px',
          top: isOpen ? 'auto' : '50%',
          bottom: isOpen ? '80px' : 'auto',
          transform: 'translateX(-50%)',
          backgroundImage: 'linear-gradient(to top left, rgba(236, 72, 153, 0.22), rgba(59, 130, 246, 0.22))',
          pointerEvents: isOpen ? 'auto' : 'none'
        }}
      >
        <div className="container-title flex items-center justify-between p-3 md:p-4 gap-2 md:gap-3">
          <div className="flex items-center gap-2 md:gap-3">
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" className={`text-pink-500 ${isRecording ? 'animate-pulse' : ''}`}>
              <path d="M20.5346 6.34625L20.3501 6.7707C20.3213 6.83981 20.2727 6.89885 20.2103 6.94038C20.148 6.98191 20.0748 7.00407 19.9999 7.00407C19.925 7.00407 19.8518 6.98191 19.7895 6.94038C19.7272 6.89885 19.6785 6.83981 19.6497 6.7707L19.4652 6.34625C19.1409 5.59538 18.5469 4.99334 17.8004 4.65894L17.2312 4.40472C17.1622 4.37296 17.1037 4.32206 17.0627 4.25806C17.0217 4.19406 16.9999 4.11965 16.9999 4.04364C16.9999 3.96763 17.0217 3.89322 17.0627 3.82922C17.1037 3.76522 17.1622 3.71432 17.2312 3.68256L17.7689 3.44334C18.5341 3.09941 19.1383 2.47511 19.457 1.69904L19.6475 1.24084C19.6753 1.16987 19.7239 1.10893 19.7869 1.06598C19.8499 1.02303 19.9244 1.00006 20.0007 1.00006C20.0769 1.00006 20.1514 1.02303 20.2144 1.06598C20.2774 1.10893 20.326 1.16987 20.3539 1.24084L20.5436 1.69829C20.8619 2.47451 21.4658 3.09908 22.2309 3.44334L22.7693 3.68331C22.8382 3.71516 22.8965 3.76605 22.9373 3.82997C22.9782 3.89389 22.9999 3.96816 22.9999 4.04402C22.9999 4.11987 22.9782 4.19414 22.9373 4.25806C22.8965 4.32198 22.8382 4.37287 22.7693 4.40472L22.1994 4.65819C21.4531 4.99293 20.8594 5.59523 20.5353 6.34625" fill="currentColor"></path>
              <path d="M3 14V10" stroke="currentColor" strokeWidth="2" strokeLinecap="round"></path>
              <path d="M21 14V10" stroke="currentColor" strokeWidth="2" strokeLinecap="round"></path>
              <path d="M16.5 18V8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"></path>
              <path d="M12 22V2" stroke="currentColor" strokeWidth="2" strokeLinecap="round"></path>
              <path d="M7.5 18V6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"></path>
            </svg>
            <p className="text-lg md:text-xl font-medium text-transparent bg-clip-text" style={{ 
              backgroundImage: isProcessing 
                ? 'linear-gradient(to right, #f59e0b, #f97316, #f59e0b)' 
                : isPlaying
                  ? 'linear-gradient(to right, #3b82f6, #8b5cf6, #3b82f6)'
                  : 'linear-gradient(to right, #ec4899, #3b82f6, #ec4899)', 
              backgroundSize: '800px', 
              animation: 'animation-color-text 8s infinite linear' 
            }}>
              {isProcessing ? 'Processing...' : isRecording ? 'Recording...' : isPlaying ? 'Speaking...' : <><span>I'm</span><span>Listening...</span></>}
            </p>
          </div>
          <button 
            onClick={closeChat}
            className="text-gray-500 hover:text-gray-700 p-1 rounded-full hover:bg-gray-200 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        
        <div className="container-chat relative flex flex-col w-full h-full text-base md:text-lg rounded-[1.5rem] overflow-hidden">
          <div className="flex z-[999] overflow-y-auto" style={{ WebkitMask: 'linear-gradient(0deg, white 85%, transparent 95% 100%)', mask: 'linear-gradient(0deg, white 85%, transparent 95% 100%)' }}>
            <div className="flex flex-col p-6 md:p-8 pb-4 pt-4 gap-3 w-full">
              {messages.map((message) => (
                <div 
                  key={message.id} 
                  className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
                >
                  {message.isUser ? (
                    <p className="w-[85%] flex flex-wrap gap-1 md:gap-2 leading-relaxed p-3 md:p-4 text-base md:text-lg text-white bg-white/20 rounded-t-xl rounded-br-xl">
                      {message.text}
                    </p>
                  ) : (
                    <div className="w-[85%] leading-relaxed p-3 md:p-4 text-base md:text-lg text-white/90 bg-black/30 rounded-t-xl rounded-br-xl">
                      {renderMessageText(message.text)}
                    </div>
                  )}
                </div>
              ))}
              {isRecording && (
                <div className="flex justify-start">
                  <p className="w-[85%] flex items-center gap-2 leading-relaxed p-3 md:p-4 text-base md:text-lg text-pink-500">
                    <span className="w-2 h-2 bg-pink-500 rounded-full animate-pulse"></span>
                    Listening...
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes circle2 {
          0% { transform: scale(1.5); }
          15% { transform: scale(1.53); }
          30% { transform: scale(1.48); }
          45% { transform: scale(1.44); }
          60% { transform: scale(1.47); }
          85% { transform: scale(1.53); }
          100% { transform: scale(1.5); }
        }
        
        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }
        
        @keyframes wave {
          0%, 100% { transform: scale(1); }
          25% { transform: scale(1.08); }
          50% { transform: scale(1.15); }
          75% { transform: scale(1.08); }
        }
        
        @keyframes animation-color-text {
          0% { background-position: -800px; }
          50% { background-position: 0px; }
        }
        
        .orb:hover {
          transform: ${isOpen ? 'translateX(-50%) scale(1.1)' : 'scale(1.4) translate(-50%, -50%)'} !important;
        }

        .orb.recording .ball {
          animation: pulse 0.5s ease-in-out infinite !important;
        }
        
        .orb.playing .ball {
          animation: wave 0.8s ease-in-out infinite !important;
        }
      `}</style>
    </div>
  )
}

export default ChatUI