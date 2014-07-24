import java.io.IOException;
import java.io.PrintWriter;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;


public class display {  
    public static void dosomething(boolean sleep)
    {
    	Connection con = null;
        try {
            //con = DriverManager.getConnection("jdbc:hsqldb:mydatabase","SA","");
        	String str = "jdbc:hsqldb:file:/home/ramnatthan/workload_snapshots/hsqldb/replayedsnapshot/mydatabase";
        	con = DriverManager.getConnection(str);
        	
            PreparedStatement pst=con.prepareStatement("select * from contacts");
            pst.clearParameters();
            ResultSet rs=pst.executeQuery();
            while(rs.next()){
                System.out.println(rs.getString(1));
                System.out.println(rs.getString(2));
                System.out.println(rs.getString(3));
            }
        
        	if(sleep){}
        		//Thread.sleep(Long.MAX_VALUE);
            
        	con.close();
        } catch (SQLException e) {
            e.printStackTrace(System.out);
        }
    }
}