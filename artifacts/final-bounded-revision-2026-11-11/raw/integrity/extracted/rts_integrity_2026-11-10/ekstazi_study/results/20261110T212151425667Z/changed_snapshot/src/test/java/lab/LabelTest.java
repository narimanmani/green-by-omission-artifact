package lab;
import org.junit.Test;
import static org.junit.Assert.assertEquals;
public class LabelTest {
    @Test public void labelContract() { assertEquals("ready", Label.value()); }
}
