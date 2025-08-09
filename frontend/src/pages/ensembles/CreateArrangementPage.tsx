import { useState, useEffect } from "react";
import {
  Container,
  Button,
  Title,
  Text,
  Notification,
  TextInput,
  Box,
  SegmentedControl,
  Group,
  Alert,
  Loader,
} from "@mantine/core";
import { X, } from "lucide-react";
import { apiService } from '../../services/apiService';
import { useParams } from "react-router-dom";
import '../../fonts.css'

export default function CreateArrangementPage() {
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState<string>("")
  const [subtitle, setSubtitle] = useState<string>("")
  const [composer, setComposer] = useState<string>("")
  const [actNumber, setActNumber] = useState<number|null>(null)
  const [pieceNumber, setPieceNumber] = useState<number|null>(null)
  const [selectedStyle, setSelectedStyle] = useState<string>("broadway")

  const [ensemble, setEnsemble] = useState<any>("");
  const { slug } = useParams();

  const [loading, setLoading] = useState(true);

  const previewStyleOptions = {
    "broadway": {
      "title": {
        margin: '0 0 8px 0',
        textDecoration: 'underline',
        fontFamily: "Palatino, sans-serif",
      },
      "subtitle": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Palatino, sans-serif",
      },
      "composer": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Palatino, sans-serif",
      },
      "mvtNo": {
        margin: 0, 
        fontSize: '1.5rem',
        fontFamily: "Palatino, sans-serif",
      },
      "partName": {
        fontFamily: "Palatino, sans-serif",
      }
    },
    "classical": {
      "title": {
        margin: '0 0 8px 0',
        textDecoration: 'underline',
        fontFamily: "Palatino, sans-serif",
      },
      "subtitle": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Palatino, sans-serif",
      },
      "composer": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Palatino, sans-serif",
      },
      "mvtNo": {
        margin: 0, 
        fontSize: '1.5rem',
        fontFamily: "Palatino, sans-serif",
      },
      "partName": {
        fontFamily: "Palatino, sans-serif",
      }
    },
    "jazz": {
      "title": {
        margin: '0 0 8px 0',
        textDecoration: 'underline',
        fontFamily: "Inkpen2, sans-serif",
      },
      "subtitle": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Inkpen2, sans-serif",
      },
      "composer": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Inkpen2, sans-serif",
      },
      "mvtNo": {
        margin: 0, 
        fontSize: '1.5rem',
        fontFamily: "Inkpen2, sans-serif",
      },
      "partName": {
        fontFamily: "Inkpen2, sans-serif",
      }
    },
  }

  // Create mvtNo variable
  const mvtNo = (actNumber && pieceNumber) ? `${actNumber}-${pieceNumber}` : "";

  //get ensemble info
  useEffect(() => {
      const fetchData = async () => {
        try {
          setLoading(true);
          // Fetch both ensemble details and arrangements
          const [ensembleData] = await Promise.all([
            apiService.getEnsemble(slug),
          ]);
          setEnsemble(ensembleData);
        } catch (err) {
          if (err instanceof Error) {
            setError(err.message);
          }
        } finally {
          setLoading(false);
        }
      };
  
      if (slug) {
        fetchData();
      }
    }, [slug]);

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

    if (loading) {
      return (
        <Container>
          <Group justify="center" py="xl">
            <Loader size="lg" />
            <Text>Loading arrangements...</Text>
          </Group>
        </Container>
      );
    }
  
    if (error) {
      return (
        <Container>
          <Alert color="red" title="Error loading arrangements">
            {error}
          </Alert>
        </Container>
      );
    }
  
    if (!ensemble) {
      return (
        <Container>
          <Alert color="yellow" title="Ensemble not found">
            The ensemble you're looking for doesn't exist.
          </Alert>
        </Container>
      );
    }


  return (
    <Container size="sm" py="xl">
      <Title ta="center" mb="xl">
        Create an Arrangement
      </Title>
      <TextInput
        disabled
        label="Ensemble Name"
        value={slug}
        mt="md"
        //TODO: This should not be editable -- just display it as a field of some kind
        // like, /app/ensembles/<slug>/create -- and get slug from that
      />
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
      <TextInput
        label="Composer"
        value={composer}
        onChange={(e) => setComposer(e.currentTarget.value)}
        mt="md"
      />
      <Text mt="md"> If you're not sure what this means, don't worry about it, you can set it later.</Text>
      <TextInput
        label="Act Number"
        value={actNumber}
        onChange={(e) => setActNumber(e.currentTarget.value)}
        type="number"
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
        mt="md"
        value={selectedStyle}
        onChange={setSelectedStyle}
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
        {title && (
          <h3 style={previewStyleOptions[selectedStyle].partName}> Conductor Score</h3>
        )}
        
        
        {(mvtNo || pieceNumber) && (selectedStyle == "broadway") && (
          <Box
            style={{
              position: 'absolute',
              top: '16px',
              right: '16px'
            }}
            bd="2px solid "
            p="sm"
          >
            <h1 style={previewStyleOptions[selectedStyle].mvtNo}>
              {mvtNo || pieceNumber}
            </h1>
          </Box>
        )}
        
        <div style={{ textAlign: 'center' }}>
          {title && (
            <h1 style={previewStyleOptions[selectedStyle].title}>
              {title}
            </h1>
          )}
          
          {subtitle && (
            <h3 style={previewStyleOptions[selectedStyle].subtitle}>
              {subtitle}
            </h3>
          )}
        </div>
        <div style={{textAlign: 'right'}}>
          {composer && (
            <h4 style={previewStyleOptions[selectedStyle].composer}>
              {composer}
            </h4>
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