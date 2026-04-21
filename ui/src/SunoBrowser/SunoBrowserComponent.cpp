#include "SunoBrowserComponent.h"

SunoBrowserComponent::SunoBrowserComponent()
{
    // Title
    titleLabel.setText("Suno Library", juce::dontSendNotification);
    titleLabel.setFont(juce::Font(18.0f, juce::Font::bold));
    addAndMakeVisible(&titleLabel);

    // Search
    searchEditor.setTextToShowWhenEmpty("Search tracks...", juce::Colours::grey);
    searchEditor.addListener(this);
    addAndMakeVisible(&searchEditor);

    // Genre filter
    genreComboBox.addItem("All Genres", 1);
    genreComboBox.addItem("Electronic", 2);
    genreComboBox.addItem("Pop", 3);
    genreComboBox.addItem("Rock", 4);
    genreComboBox.addItem("Hip Hop", 5);
    genreComboBox.setSelectedId(1);
    addAndMakeVisible(&genreComboBox);

    // Tempo range
    tempoMinSlider.setRange(60, 200, 1);
    tempoMinSlider.setValue(80);
    tempoMinSlider.setTextBoxStyle(juce::Slider::TextEntryBoxPosition::TextBoxRight, false, 40, 20);
    addAndMakeVisible(&tempoMinSlider);

    tempoMaxSlider.setRange(60, 200, 1);
    tempoMaxSlider.setValue(160);
    tempoMaxSlider.setTextBoxStyle(juce::Slider::TextEntryBoxPosition::TextBoxRight, false, 40, 20);
    addAndMakeVisible(&tempoMaxSlider);
    tempoRangeLabel.setText("BPM Range:", juce::dontSendNotification);
    addAndMakeVisible(&tempoRangeLabel);

    // Status label
    statusLabel.setText("Loading...", juce::dontSendNotification);
    statusLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(&statusLabel);

    // Table
    trackTable.setModel(this);
    trackTable.setColour(juce::ListBox::outlineColourId, juce::Colours::grey);
    trackTable.setOutlineThickness(1);

    // Add columns
    trackTable.getHeader().addColumn("Title", TitleColumn, 200, 100, 400, juce::TableHeaderComponent::defaultFlags);
    trackTable.getHeader().addColumn("Artist", ArtistColumn, 150, 80, 300, juce::TableHeaderComponent::defaultFlags);
    trackTable.getHeader().addColumn("Genre", GenreColumn, 100, 60, 150, juce::TableHeaderComponent::defaultFlags);
    trackTable.getHeader().addColumn("Tempo", TempoColumn, 60, 50, 80, juce::TableHeaderComponent::defaultFlags);
    trackTable.getHeader().addColumn("Key", KeyColumn, 50, 40, 60, juce::TableHeaderComponent::defaultFlags);
    trackTable.getHeader().addColumn("Action", ActionColumn, 80, 60, 100, juce::TableHeaderComponent::defaultFlags);

    addAndMakeVisible(&trackTable);

    // Buttons
    refreshButton.setButtonText("Refresh");
    refreshButton.addListener(this);
    addAndMakeVisible(&refreshButton);

    importButton.setButtonText("Import");
    importButton.addListener(this);
    importButton.setEnabled(false);
    addAndMakeVisible(&importButton);

    // Initial load
    loadTracks();
}

SunoBrowserComponent::~SunoBrowserComponent()
{
    searchEditor.removeListener(this);
    refreshButton.removeListener(this);
    importButton.removeListener(this);
}

void SunoBrowserComponent::paint(juce::Graphics& g)
{
    g.fillAll(getLookAndFeel().findColour(juce::ResizableWindow::backgroundColourId));
}

void SunoBrowserComponent::resized()
{
    auto area = getLocalBounds().reduced(10);

    // Title
    titleLabel.setBounds(area.removeFromTop(headerHeight));

    // Filters row
    auto filterRow = area.removeFromTop(filterHeight);
    searchEditor.setBounds(filterRow.removeFromLeft(200));
    filterRow.removeFromLeft(10);
    genreComboBox.setBounds(filterRow.removeFromLeft(120));
    filterRow.removeFromLeft(20);
    tempoRangeLabel.setBounds(filterRow.removeFromLeft(70));
    tempoMinSlider.setBounds(filterRow.removeFromLeft(80));
    filterRow.removeFromLeft(5);
    tempoMaxSlider.setBounds(filterRow.removeFromLeft(80));
    filterRow.removeFromLeft(20);
    refreshButton.setBounds(filterRow.removeFromRight(buttonWidth));

    area.removeFromTop(10);

    // Status label (shown when loading)
    if (!statusLabel.getText().isEmpty() && tracks.empty())
    {
        statusLabel.setBounds(area.removeFromTop(30));
        area.removeFromTop(10);
    }

    // Table and import button
    auto bottomRow = area.removeFromBottom(40);
    importButton.setBounds(bottomRow.removeFromRight(buttonWidth));

    trackTable.setBounds(area);
}

// TableListBoxModel interface
int SunoBrowserComponent::getNumRows()
{
    return static_cast<int>(tracks.size());
}

void SunoBrowserComponent::paintRowBackground(juce::Graphics& g, int rowNumber, int width, int height, bool rowIsSelected)
{
    if (rowIsSelected)
        g.fillAll(juce::Colours::lightblue.withAlpha(0.3f));
    else if (rowNumber % 2 == 0)
        g.fillAll(juce::Colours::white.withAlpha(0.1f));
}

void SunoBrowserComponent::paintCell(juce::Graphics& g, int rowNumber, int columnId, int width, int height, bool rowIsSelected)
{
    if (rowNumber < 0 || rowNumber >= static_cast<int>(tracks.size()))
        return;

    const auto& track = tracks[rowNumber];
    juce::String text;

    switch (columnId)
    {
        case TitleColumn: text = track.title; break;
        case ArtistColumn: text = track.artist; break;
        case GenreColumn: text = track.genre; break;
        case TempoColumn: text = juce::String(track.tempo); break;
        case KeyColumn: text = track.key; break;
        default: return;
    }

    g.setColour(rowIsSelected ? juce::Colours::black : juce::Colours::white);
    g.setFont(14.0f);
    g.drawText(text, 5, 0, width - 10, height, juce::Justification::centredLeft, true);
}

juce::Component* SunoBrowserComponent::refreshComponentForCell(int rowNumber, int columnId, bool isRowSelected, juce::Component* existingComponentToUpdate)
{
    if (columnId != ActionColumn)
        return existingComponentToUpdate;

    // Create button for action column
    auto* button = dynamic_cast<juce::TextButton*>(existingComponentToUpdate);
    if (button == nullptr)
    {
        button = new juce::TextButton("Import");
        button->onClick = [this, rowNumber]
        {
            if (rowNumber >= 0 && rowNumber < static_cast<int>(tracks.size()))
            {
                selectedRow = rowNumber;
                importButton.setEnabled(true);
                importSelectedTrack();
            }
        };
    }

    return button;
}

// TextEditor::Listener
void SunoBrowserComponent::textEditorTextChanged(juce::TextEditor& editor)
{
    if (&editor == &searchEditor)
    {
        // Trigger search with debounce
        auto query = searchEditor.getText();
        auto genre = genreComboBox.getSelectedId() == 1 ? juce::String() : genreComboBox.getText();
        searchTracks(query, genre, static_cast<int>(tempoMinSlider.getValue()), static_cast<int>(tempoMaxSlider.getValue()));
    }
}

// Button::Listener
void SunoBrowserComponent::buttonClicked(juce::Button* button)
{
    if (button == &refreshButton)
    {
        loadTracks();
    }
    else if (button == &importButton)
    {
        importSelectedTrack();
    }
}

void SunoBrowserComponent::importSelectedTrack()
{
    if (selectedRow >= 0 && selectedRow < static_cast<int>(tracks.size()))
    {
        const auto& track = tracks[selectedRow];
        
        // Download WAV file from API
        juce::String wavUrl = "http://127.0.0.1:3000/api/tracks/" + track.id + "/wav";
        juce::URL apiUrl(wavUrl);
        
        statusLabel.setText("Downloading " + track.title + "...", juce::dontSendNotification);
        
        // Download to temp file
        auto tempDir = juce::File::getSpecialLocation(juce::File::tempDirectory);
        auto tempFile = tempDir.getChildFile("suno_" + track.id + ".wav");
        
        // Use async download
        auto stream = apiUrl.createInputStream(juce::URL::InputStreamOptions(juce::URL::ParameterHandling::inAddress)
            .withConnectionTimeoutMs(30000)
            .withNumRedirectsToFollow(3));
        
        if (stream != nullptr)
        {
            juce::MemoryBlock data;
            auto bytesRead = stream->readIntoMemoryBlock(data);
            
            if (bytesRead > 0 && data.getSize() > 0)
            {
                // Save to temp file
                if (tempFile.replaceWithData(data.getData(), static_cast<int>(data.getSize())))
                {
                    statusLabel.setText("Imported: " + track.title, juce::dontSendNotification);
                    
                    if (onTrackImported)
                        onTrackImported(track.id, 0, 0, tempFile.getFullPathName());
                }
                else
                {
                    statusLabel.setText("Failed to save: " + track.title, juce::dontSendNotification);
                }
            }
            else
            {
                statusLabel.setText("Failed to download: " + track.title, juce::dontSendNotification);
            }
        }
        else
        {
            statusLabel.setText("Failed to connect for: " + track.title, juce::dontSendNotification);
        }
    }
}

void SunoBrowserComponent::loadTracks()
{
    statusLabel.setText("Loading tracks...", juce::dontSendNotification);
    fetchTracksFromAPI();
}

void SunoBrowserComponent::searchTracks(const juce::String& query, const juce::String& genre, int tempoMin, int tempoMax)
{
    // Build search URL with parameters
    juce::String url = "http://127.0.0.1:3000/api/search?q=" + juce::URL::addEscapeChars(query, true);
    if (genre.isNotEmpty())
        url += "&genre=" + juce::URL::addEscapeChars(genre, true);
    url += "&tempo_min=" + juce::String(tempoMin);
    url += "&tempo_max=" + juce::String(tempoMax);

    // JUCE 7: Synchronous HTTP read with async UI update
    juce::URL apiUrl(url);
    auto stream = apiUrl.createInputStream(juce::URL::InputStreamOptions(juce::URL::ParameterHandling::inAddress)
        .withConnectionTimeoutMs(5000)
        .withNumRedirectsToFollow(3));
    
    if (stream != nullptr)
    {
        juce::MemoryBlock data;
        auto bytesRead = stream->readIntoMemoryBlock(data);
        bool success = bytesRead > 0;
        
        juce::MessageManager::callAsync([this, data, success]() {
            if (success && data.getSize() > 0)
            {
                juce::String response(data.toString());
                parseTracksResponse(response);
            }
            else
            {
                statusLabel.setText("Failed to load tracks", juce::dontSendNotification);
                trackTable.updateContent();
            }
        });
    }
    else
    {
        statusLabel.setText("Failed to connect", juce::dontSendNotification);
        trackTable.updateContent();
    }
}

void SunoBrowserComponent::fetchTracksFromAPI()
{
    juce::URL apiUrl("http://127.0.0.1:3000/api/tracks");
    
    // JUCE 7: Synchronous HTTP read with async UI update
    auto stream = apiUrl.createInputStream(juce::URL::InputStreamOptions(juce::URL::ParameterHandling::inAddress)
        .withConnectionTimeoutMs(5000)
        .withNumRedirectsToFollow(3));
    
    if (stream != nullptr)
    {
        juce::MemoryBlock data;
        auto bytesRead = stream->readIntoMemoryBlock(data);
        bool success = bytesRead > 0;
        
        juce::MessageManager::callAsync([this, data, success]() {
            if (success && data.getSize() > 0)
            {
                juce::String response(data.toString());
                parseTracksResponse(response);
            }
            else
            {
                statusLabel.setText("API not available - using demo data", juce::dontSendNotification);
                loadMockData();
            }
        });
    }
    else
    {
        // Fallback to mock data
        statusLabel.setText("API not available - using demo data", juce::dontSendNotification);
        loadMockData();
    }
}

void SunoBrowserComponent::loadMockData()
{
    tracks.clear();
    tracks.push_back({"1", "Demo Track 1", "AI Artist", "Electronic", 128, "C", "/path/to/track1.mp3"});
    tracks.push_back({"2", "Demo Track 2", "AI Artist", "Pop", 120, "G", "/path/to/track2.mp3"});
    tracks.push_back({"3", "Demo Track 3", "AI Artist", "Rock", 140, "E", "/path/to/track3.mp3"});
    trackTable.updateContent();
    resized();
}

void SunoBrowserComponent::parseTracksResponse(const juce::String& jsonResponse)
{
    tracks.clear();

    // Parse JSON using juce::JSON
    auto jsonResult = juce::JSON::parse(jsonResponse);
    
    // JUCE 7: Check if parse failed by checking if result is undefined/null
    if (jsonResult.isUndefined() || jsonResult.isVoid())
    {
        statusLabel.setText("Failed to parse response", juce::dontSendNotification);
        trackTable.updateContent();
        resized();
        return;
    }

    auto* json = jsonResult.getDynamicObject();
    if (json == nullptr)
    {
        statusLabel.setText("Invalid response format", juce::dontSendNotification);
        trackTable.updateContent();
        resized();
        return;
    }

    // Get tracks array
    auto tracksVar = json->getProperty("tracks");
    if (!tracksVar.isArray())
    {
        statusLabel.setText("No tracks found", juce::dontSendNotification);
        trackTable.updateContent();
        resized();
        return;
    }

    auto* tracksArray = tracksVar.getArray();
    for (const auto& trackVar : *tracksArray)
    {
        if (!trackVar.isObject())
            continue;

        auto* trackObj = trackVar.getDynamicObject();
        if (trackObj == nullptr)
            continue;

        TrackInfo info;
        info.id = trackObj->getProperty("id").toString();
        info.title = trackObj->getProperty("title").toString();
        info.artist = trackObj->getProperty("artist").toString();
        info.genre = trackObj->getProperty("genre").toString();
        info.tempo = trackObj->getProperty("tempo");
        info.key = trackObj->getProperty("key").toString();
        info.audioPath = trackObj->getProperty("audio_path").toString();

        // Handle numeric fields that might be strings
        if (info.tempo == 0)
        {
            juce::String tempoStr = trackObj->getProperty("tempo").toString();
            info.tempo = tempoStr.getIntValue();
        }

        tracks.push_back(info);
    }

    if (tracks.empty())
    {
        statusLabel.setText("No tracks found", juce::dontSendNotification);
    }
    else
    {
        statusLabel.setText(juce::String(tracks.size()) + " tracks loaded", juce::dontSendNotification);
    }

    trackTable.updateContent();
    resized();
}
