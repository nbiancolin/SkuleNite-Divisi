import { useState } from "react";
import {
  Container,
  Button,
  Title,
  Text,
  Notification,
  TextInput,
  Box,
  SegmentedControl,
} from "@mantine/core";
import { X, } from "lucide-react";
import { apiService } from '../../services/apiService';


export default function CreateArrangementPage() {
  const [error, setError] = useState<string | null>(null);
  const [ensembleSlug, setEnsembleSlug] = useState<string>("")
  const [title, setTitle] = useState<string>("")
  const [subtitle, setSubtitle] = useState<string>("")
  const [actNumber, setActNumber] = useState<number|null>(null)
  const [pieceNumber, setPieceNumber] = useState<number|null>(null)
  const [selectedStyle, setSelectedStyle] = useState<string>("broadway")

  // Create mvtNo variable
  const mvtNo = (actNumber && pieceNumber) ? `${actNumber}-${pieceNumber}` : "";
  

  const createArrangment = async () => {

    try {
      const data = await apiService.createArrangement(ensembleName)
      
      window.location.href = `/app/ensembles/${data.ensembleSlug}/arrangements`;
      //once finished, redirect to that ensebles page (for testing, use all ensembles page
    } catch (err: any) {
      console.error("Error when creating arrangement:", err);
      setError(err.response?.data?.detail || "Formatting failed.");  //TODO[SC-XX] make this acc display the error at hand
    } 
  };

  return (
    <Container size="sm" py="xl">
      <Title ta="center" mb="xl">
        Create an Arrangement
      </Title>
      <Text>Enter the name of your ensemble.</Text>
      <Text>Note that ensemble names are unique.</Text>
      {/* <TextInput
        label="Ensemble Name"
        value={ensembleSlug}
        onChange={(e) => setEnsembleSlug(e.currentTarget.value)}
        mt="md"
        //TODO: This should not be editable -- just display it as a field of some kind
        // like, /app/ensembles/<slug>/create -- and get slug from that
      /> */}
      <TextInput
        label="Arrangement Title"
        value={title}
        onChange={(e) => setTitle(e.currentTarget.value)}
        mt="md"
        required
      />
      <TextInput
        label="Subtitle"
        value={subtitle}
        onChange={(e) => setSubtitle(e.currentTarget.value)}
        mt="md"
      />
      <Text> If you're not sure what this means, don't worry about it, you can set it later.</Text>
      <TextInput
        label="Act Number"
        value={actNumber}
        onChange={(e) => setActNumber(e.currentTarget.value)}
        type="number"
        mt="md"
      />
      <TextInput
        label="Piece Number"
        value={pieceNumber}
        onChange={(e) => setPieceNumber(e.currentTarget.value)}
        type="number"
        mt="md"
      />

      <SegmentedControl 
        fullWidth
        size="md"
        value={selectedStyle}
        onChange={(e) => setSelectedStyle(e.currentTarget.value)}
        data={[
          {label: "Broadway", value: "broadway"},
          {label: "Jazz", value: "jazz"},
          {label: "Classical", value: "classical"},
        ]}
      />

      {/* Preview of the header */}
      <Box
        mt="xl"
        mb="xl"
        p="md"
        style={{
          border: '1px solid #dee2e6',
          borderRadius: '8px',
          width: '100%',
          position: 'relative'
        }}
      >
        <Text size="sm" mb="md" style={{ color: '#666' }}>
          Title Preview:
        </Text>
        
        {(mvtNo || pieceNumber) && (
          <Box
            style={{
              position: 'absolute',
              top: '16px',
              right: '16px'
            }}
            bd="1px solid red.6"
          >
            <h1 style={{ margin: 0, fontSize: '1.5rem' }}>
              {mvtNo || pieceNumber}
            </h1>
          </Box>
        )}
        
        <div style={{ textAlign: 'center' }}>
          {title && (
            <h1 style={{ margin: '0 0 8px 0' }}>
              {title}
            </h1>
          )}
          
          {subtitle && (
            <h3 style={{ margin: '0', fontWeight: 'normal' }}>
              {subtitle}
            </h3>
          )}
        </div>
        
        {!title && !subtitle && !mvtNo && (
          <Text style={{ color: '#999', fontStyle: 'italic', textAlign: 'center' }}>
            Fill in the fields above to see a preview of your arrangement header
          </Text>
        )}
      </Box>

      <Button
        onClick={createArrangment}
        fullWidth
      >
        Create Arrangement
      </Button>

      {error && (
        <Notification
          mt="xl"
          icon={<X size={18} />}
          color="red"
          title="Error"
          onClose={() => setError(null)}
        >
          {error}
        </Notification>
      )}
    </Container>
  );
}