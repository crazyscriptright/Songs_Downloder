import { Routes, Route } from 'react-router-dom'
import MusicDownloader from './pages/MusicDownloader'
import BulkDownloader from './pages/BulkDownloader'

function App() {
  return (
    <Routes>
      <Route path="/" element={<MusicDownloader />} />
      <Route path="/bulk" element={<BulkDownloader />} />
    </Routes>
  )
}

export default App
