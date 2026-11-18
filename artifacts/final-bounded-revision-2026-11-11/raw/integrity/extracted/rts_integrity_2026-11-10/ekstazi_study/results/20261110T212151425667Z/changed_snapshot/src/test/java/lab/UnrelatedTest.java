package lab;
import org.junit.Test;
import static org.junit.Assert.assertEquals;
public class UnrelatedTest {
    @Test public void unrelatedContract() { assertEquals(7, Unrelated.value()); }
}
