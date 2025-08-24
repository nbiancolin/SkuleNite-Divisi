import { useState, useEffect } from "react";
import {
  Container,
  Button,
  Title,
  Text,
  Notification,
  TextInput,
  Group,
  Alert,
  Loader,
} from "@mantine/core";
import { X, } from "lucide-react";
import { apiService } from '../../services/apiService';
import type { Ensemble, Arrangement } from "../../services/apiService";
import { useNavigate, useParams } from "react-router-dom";
import '../../fonts.css'
import { ScoreTitlePreview } from "../../components/ScoreTitlePreview";
import type { PreviewStyleName } from "../../components/ScoreTitlePreview";

export default function CreateArrangementPage() {

  const emptyArrangement = (): Arrangement => ({
  id: 0,
  ensemble: 0, 
  ensemble_name: "ens",
  ensemble_slug: "ens-slug",
  title: "",
  subtitle: "",
  style: "broadway",
  slug: "",
  composer: "",
  actNumber: 0,
  pieceNumber: 0,
  mvt_no: "",
  latest_version: {
    id: 0,
    uuid: "",
    arrangementId: 0,
    versionNum: "0.0.0",
    timestamp: ""
  },
  latest_version_num: "N/A",
})

const emptyEnsemble = (): Ensemble => ({
  id: 0,
  name: '',
  slug: '',
  arrangements: [emptyArrangement()],
})

  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState<string>("")
  const [subtitle, setSubtitle] = useState<string>("")
  const [composer, setComposer] = useState<string>("")
  const [actNumber, setActNumber] = useState<string>("")
  const [pieceNumber, setPieceNumber] = useState<string>("")
  const [selectedStyle, setSelectedStyle] = useState<PreviewStyleName>("broadway")

  const [ensemble, setEnsemble] = useState<Ensemble>(emptyEnsemble());
  const { slug = "NA" } = useParams();

  const [loading, setLoading] = useState(true);

  const navigate = useNavigate()

  const mvtNo = (actNumber && pieceNumber) ? `${actNumber}-${pieceNumber}` : "";

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
      await apiService.createArrangement(ensemble.id, title, subtitle, composer, actNumber, pieceNumber, selectedStyle)

      navigate(`/app/ensembles/${ensemble.slug}/arrangements`)
    } catch (err) {
      if (err instanceof Error){
        console.error("Error when creating arrangement:", err.message);
        setError(err.message || "Unknown Error."); 
      }
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
        type="number"
        onChange={(e) => setActNumber(e.currentTarget.value)}  //+ Operator converts from string to number (so stupid but wtv)
      />
      <TextInput
        label="Piece Number"
        value={pieceNumber}
        onChange={(e) => setPieceNumber(e.currentTarget.value)}
        type="number"
        mt="md"
      />

      <ScoreTitlePreview
        selectedStyle={selectedStyle}
        setSelectedStyle={setSelectedStyle}
        title={title}
        ensemble={slug}
        subtitle={subtitle}
        composer={composer}
        arranger={null}
        mvtNo={mvtNo}
        showTitle={null}
        pieceNumber={+pieceNumber}
      />

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