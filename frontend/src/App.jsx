import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import ChatUI from './components/ChatUI'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ChatUI />} />
        <Route path="/chat" element={<ChatUI />} />
      </Routes>
    </Router>
  )
}

export default App