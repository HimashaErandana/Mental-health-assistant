import { createContext, useContext, useState } from 'react'

const AppContext = createContext()

export function AppProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isRecording, setIsRecording] = useState(false)
  const [messages, setMessages] = useState([])

  const addMessage = (message) => {
    setMessages(prev => [...prev, message])
  }

  const clearMessages = () => {
    setMessages([])
  }

  return (
    <AppContext.Provider value={{
      user,
      setUser,
      isRecording,
      setIsRecording,
      messages,
      addMessage,
      clearMessages
    }}>
      <div className="min-h-screen bg-[#000080]">
        {children}
      </div>
    </AppContext.Provider>
  )
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within AppProvider')
  }
  return context
}