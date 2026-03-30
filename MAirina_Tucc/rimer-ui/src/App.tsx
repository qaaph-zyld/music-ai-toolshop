import { useState } from 'react'
import { Search, ListMusic, BrainCircuit, Type, Sparkles } from 'lucide-react'
import axios from 'axios'
import { Button } from './components/ui/button'

function App() {
  const [activeTab, setActiveTab] = useState('editor')
  const [word, setWord] = useState('')
  const [rhymes, setRhymes] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [consonants, setConsonants] = useState<string[]>([])

  const findRhymes = async (w: string) => {
    if (!w) return
    setLoading(true)
    try {
      const res = await axios.post('/api/rhymes', { word: w, max_results: 20 })
      setRhymes(res.data.rhymes)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  const findConsonants = async (w: string) => {
    if (!w) return
    setLoading(true)
    try {
      const res = await axios.post('/api/consonant-play', { word: w, match_type: 'hard', max_results: 20 })
      setConsonants(res.data.matches)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  return (
    <div className="flex h-screen bg-background text-foreground w-full text-left">
      {/* Sidebar */}
      <div className="w-16 border-r border-border flex flex-col items-center py-4 gap-6 bg-muted/20">
        <div className="w-10 h-10 rounded-xl bg-primary text-primary-foreground flex items-center justify-center font-bold text-xl mb-4">
          M
        </div>
        <button 
          onClick={() => setActiveTab('editor')}
          className={`p-3 rounded-lg transition-colors ${activeTab === 'editor' ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground hover:bg-secondary/50'}`}
          title="Editor"
        >
          <Type size={20} />
        </button>
        <button 
          onClick={() => setActiveTab('tools')}
          className={`p-3 rounded-lg transition-colors ${activeTab === 'tools' ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground hover:bg-secondary/50'}`}
          title="AI Tools"
        >
          <BrainCircuit size={20} />
        </button>
        <button 
          onClick={() => setActiveTab('projects')}
          className={`p-3 rounded-lg transition-colors ${activeTab === 'projects' ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground hover:bg-secondary/50'}`}
          title="Projects"
        >
          <ListMusic size={20} />
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <header className="h-14 border-b border-border flex items-center px-6 bg-background">
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <Sparkles size={18} className="text-primary" />
            MAirina Tucc <span className="text-muted-foreground text-sm font-normal ml-2">Serbian Songwriting Suite</span>
          </h1>
        </header>

        <main className="flex-1 overflow-auto p-6 flex gap-6">
          {/* Editor Area */}
          <div className="flex-1 flex flex-col">
            <div className="mb-4 flex justify-between items-center">
              <h2 className="text-2xl font-bold">New Song Draft</h2>
              <Button variant="outline" size="sm">Save Draft</Button>
            </div>
            <textarea 
              className="flex-1 w-full bg-background border border-input rounded-md p-4 resize-none focus:outline-none focus:ring-2 focus:ring-ring font-medium text-lg leading-relaxed shadow-sm"
              placeholder="Start writing your lyrics here... Select a word to see suggestions."
              defaultValue="Volim te kao sunce&#10;Kao nebo nad glavom&#10;Tvoja ljubav je čudo&#10;Koje nosim sa sobom"
            />
          </div>

          {/* Tools Panel */}
          <div className="w-80 border border-border rounded-lg bg-card text-card-foreground shadow-sm flex flex-col">
            <div className="p-4 border-b border-border bg-muted/20">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Search size={16} /> Language Tools
              </h3>
              <div className="flex gap-2 mb-2">
                <input 
                  type="text" 
                  value={word}
                  onChange={(e) => setWord(e.target.value)}
                  placeholder="Enter a word..."
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      findRhymes(word)
                      findConsonants(word)
                    }
                  }}
                />
              </div>
              <div className="flex gap-2">
                <Button size="sm" className="flex-1" onClick={() => findRhymes(word)} disabled={loading}>Rhymes</Button>
                <Button size="sm" variant="secondary" className="flex-1" onClick={() => findConsonants(word)} disabled={loading}>Drill</Button>
              </div>
            </div>

            <div className="flex-1 overflow-auto p-4 flex flex-col gap-6">
              {rhymes.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">Perfect & Slant Rhymes</h4>
                  <div className="flex flex-wrap gap-2">
                    {rhymes.map(r => (
                      <span key={r} className="px-2 py-1 bg-secondary text-secondary-foreground rounded-md text-sm border border-border/50 cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors">
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {consonants.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">Consonant Play (Drill Flow)</h4>
                  <div className="flex flex-wrap gap-2">
                    {consonants.map(c => (
                      <span key={c} className="px-2 py-1 bg-accent text-accent-foreground rounded-md text-sm border border-border/50 cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors font-medium">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {rhymes.length === 0 && consonants.length === 0 && !loading && (
                <div className="text-center text-muted-foreground text-sm mt-10">
                  Enter a word or select one in the editor to see rhyme and flow suggestions.
                </div>
              )}

              {loading && (
                <div className="text-center text-muted-foreground text-sm mt-10 animate-pulse">
                  Analyzing word...
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
